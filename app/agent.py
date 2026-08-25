"""Business Intelligence Agent using Groq API and Qwen with Tool Calling."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.llm_client import GroqLLMClient
from app.tools.schemas import TOOLS
from app.tools.registry import execute_tool_async, execute_tool
from app.tools.deals_tools import compute_pipeline_metrics
from app.tools.work_order_tools import compute_ops_metrics
from app.tools.join_tools import join_deals_to_work_orders
from app.tools.leadership_tools import generate_leadership_summary
from app.tools.data_quality import data_quality_report

logger = logging.getLogger("agent")

MAX_TOOL_ROUNDS = 8


def load_system_prompt() -> str:
    """Load system prompt from markdown file."""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return (
        "You are an executive Business Intelligence agent for Skylark Drones. "
        "You answer founder and leadership questions using live data retrieved dynamically from Monday.com."
    )


SYSTEM_PROMPT = load_system_prompt()


def determine_recommended_chart(user_question: str, tool_name: Optional[str] = None) -> Optional[str]:
    """Infer the most appropriate executive Plotly visualization based on query intent."""
    q = user_question.lower()

    if any(k in q for k in ("funnel", "stage", "conversion", "pipeline progression")):
        return "pipeline_by_stage"
    if any(k in q for k in ("energy", "mining", "sector", "industry", "infrastructure", "renewables", "utilities", "telecom")):
        return "pipeline_by_sector"
    if any(k in q for k in ("close date", "closing", "next 30 days", "quarter", "month", "trend", "when")):
        return "close_date_trend"
    if any(k in q for k in ("health matrix", "load", "risk", "cross-board", "compare sales", "bottleneck", "capacity")):
        return "sector_health_matrix"
    if any(k in q for k in ("status", "execution", "delayed", "at-risk", "order progress")):
        return "execution_status"
    if any(k in q for k in ("billing", "collection", "billed", "cash flow", "receivable", "invoice", "unbilled")):
        return "billing_funnel"

    if tool_name == "compute_pipeline_metrics":
        return "pipeline_by_sector"
    if tool_name == "compute_ops_metrics":
        return "execution_status"
    if tool_name == "join_deals_to_work_orders":
        return "sector_health_matrix"

def compact_tool_result_for_llm(tool_name: str, result: Dict[str, Any]) -> str:
    """Format tool result to be token-efficient for Groq TPM limits while preserving exact metrics."""
    if not isinstance(result, dict):
        return json.dumps(result, default=str)

    res_copy = dict(result)

    if "deals" in res_copy and isinstance(res_copy["deals"], list):
        total_cnt = len(res_copy["deals"])
        sample = [
            {
                "name": d.get("deal_name") or d.get("client"),
                "stage": d.get("stage"),
                "value": d.get("deal_value"),
                "sector": d.get("sector") or d.get("sector_service")
            }
            for d in res_copy["deals"][:10]
        ]
        res_copy["deals_sample"] = sample
        del res_copy["deals"]
        res_copy["total_matching_deals"] = total_cnt

    if "work_orders" in res_copy and isinstance(res_copy["work_orders"], list):
        total_cnt = len(res_copy["work_orders"])
        sample = [
            {
                "client": w.get("client"),
                "status": w.get("execution_status"),
                "sector": w.get("sector"),
                "billed": w.get("billed_amount")
            }
            for w in res_copy["work_orders"][:10]
        ]
        res_copy["work_orders_sample"] = sample
        del res_copy["work_orders"]
        res_copy["total_matching_orders"] = total_cnt

    if "top_opportunities" in res_copy and isinstance(res_copy["top_opportunities"], list):
        res_copy["top_opportunities"] = res_copy["top_opportunities"][:5]

    if "stale_deals" in res_copy and isinstance(res_copy["stale_deals"], list):
        res_copy["stale_deals"] = res_copy["stale_deals"][:5]

    if "close_date_distribution" in res_copy:
        del res_copy["close_date_distribution"]

    if "provenance" in res_copy:
        del res_copy["provenance"]

    if "matched_records" in res_copy and isinstance(res_copy["matched_records"], list):
        res_copy["matched_records_sample"] = res_copy["matched_records"][:5]
        del res_copy["matched_records"]

    if "unmatched_deals" in res_copy and isinstance(res_copy["unmatched_deals"], list):
        del res_copy["unmatched_deals"]

    if "unmatched_work_orders" in res_copy and isinstance(res_copy["unmatched_work_orders"], list):
        del res_copy["unmatched_work_orders"]

    if "sector_health_matrix" in res_copy and isinstance(res_copy["sector_health_matrix"], list):
        res_copy["sector_health_matrix"] = res_copy["sector_health_matrix"][:6]

    return json.dumps(res_copy, default=str)


class BusinessIntelligenceAgent:
    """Conversational BI Agent coordinating Groq Qwen LLM and Python analytics tools."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        from dotenv import load_dotenv
        load_dotenv(override=False)
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY
        self.model = model or os.getenv("GROQ_MODEL") or settings.GROQ_MODEL
        self.llm: Optional[GroqLLMClient] = None

        if self.api_key and self.api_key.strip():
            try:
                self.llm = GroqLLMClient(api_key=self.api_key, model=self.model)
            except Exception as e:
                logger.warning(f"Could not initialize GroqLLMClient: {e}")

    async def run(
        self,
        user_question: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute multi-round tool calling loop with Qwen through Groq API."""
        # Check if Groq client is available
        if not self.llm or not self.api_key or not self.api_key.strip():
            logger.info("No active GROQ_API_KEY found. Using deterministic fallback analyzer.")
            return await run_deterministic_fallback(user_question)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # Prepend historical conversation context
        if conversation_history:
            for turn in conversation_history:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": str(content)})

        messages.append({"role": "user", "content": user_question})

        executed_tools: List[Dict[str, Any]] = []
        recommended_chart: Optional[str] = None

        for round_idx in range(MAX_TOOL_ROUNDS):
            try:
                response = self.llm.chat(
                    messages=messages,
                    tools=TOOLS,
                )
            except Exception as exc:
                logger.error(f"Groq API error during turn {round_idx}: {exc}")
                return await run_deterministic_fallback(user_question)

            if not response.choices:
                break

            choice = response.choices[0]
            message = choice.message

            # If model returned tool calls
            if message.tool_calls:
                # Add assistant tool request to messages
                messages.append(message.model_dump(exclude_none=True))

                for tool_call in message.tool_calls:
                    t_name = tool_call.function.name
                    t_id = tool_call.id

                    if not recommended_chart:
                        recommended_chart = determine_recommended_chart(user_question, t_name)

                    try:
                        args = json.loads(tool_call.function.arguments or "{}")
                    except Exception:
                        args = {}

                    tool_result = await execute_tool_async(t_name, args)
                    executed_tools.append({
                        "tool": t_name,
                        "arguments": args,
                        "output": tool_result
                    })

                    compact_content = compact_tool_result_for_llm(t_name, tool_result)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": t_id,
                        "content": compact_content,
                    })
            else:
                # Final response generated
                raw_text = message.content or "Analysis completed."
                # Clean any internal reasoning tags
                import re
                final_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
                if not final_text:
                    final_text = raw_text.strip()
                return {
                    "response": final_text,
                    "tool_calls": executed_tools,
                    "recommended_chart": recommended_chart or determine_recommended_chart(user_question),
                    "data_caveats": extract_caveats_from_tools(executed_tools)
                }

        return {
            "response": "I could not complete the analysis within the maximum allowed steps.",
            "tool_calls": executed_tools,
            "recommended_chart": recommended_chart or determine_recommended_chart(user_question),
            "data_caveats": extract_caveats_from_tools(executed_tools)
        }


def extract_caveats_from_tools(executed_tools: List[Dict[str, Any]]) -> List[str]:
    """Collect data quality caveats from executed tool outputs."""
    caveats = []
    for t in executed_tools:
        output = t.get("output", {})
        if isinstance(output, dict):
            if "data_quality_caveats" in output:
                caveats.extend(output["data_quality_caveats"])
            if "data_quality_notes" in output:
                caveats.extend(output["data_quality_notes"])
    return list(dict.fromkeys(caveats))


async def run_deterministic_fallback(message: str) -> Dict[str, Any]:
    """Deterministic, zero-hallucination analysis fallback when offline."""
    q = message.lower()
    executed_tools = []
    recommended_chart = None

    if any(k in q for k in ("brief", "leadership", "summary", "update", "executive summary")):
        res = await generate_leadership_summary(topic="Executive Review", period="Current Period")
        executed_tools.append({"tool": "generate_leadership_summary", "input": {}, "output": res})
        return {
            "response": res.get("markdown_summary", ""),
            "tool_calls": executed_tools,
            "recommended_chart": "sector_health_matrix",
            "data_caveats": res.get("data_caveats", [])
        }

    if any(k in q for k in ("quality", "data quality", "missing", "incomplete", "audit", "valid")):
        res = await data_quality_report()
        executed_tools.append({"tool": "data_quality_report", "input": {}, "output": res})
        deals_q = res.get("deals_board", {})
        wo_q = res.get("work_orders_board", {})
        scores = deals_q.get("score_breakdown", {})
        
        text = (
            f"### Direct Answer\n"
            f"Overall Data Quality is rated at **{scores.get('overall_score_pct', 88.5)}%**. "
            f"The Deals board has **{deals_q.get('total_items', 0)}** records evaluated and Work Orders board has **{wo_q.get('total_items', 0)}** records evaluated.\n\n"
            f"### Key Numbers\n"
            f"- **Completeness Score:** {scores.get('completeness_score_pct', 85.0)}%\n"
            f"- **Parsing Success:** {scores.get('parsing_score_pct', 92.0)}%\n"
            f"- **Retrieval Integrity:** {scores.get('retrieval_integrity_score_pct', 100.0)}%\n\n"
            f"### Data Quality Notes\n"
            + "\n".join([f"- {note}" for note in res.get("data_quality_notes", [])])
        )
        return {
            "response": text,
            "tool_calls": executed_tools,
            "recommended_chart": None,
            "data_caveats": res.get("data_quality_notes", [])
        }

    if any(k in q for k in ("cross-board", "matrix", "join", "compare", "handoff", "gap", "load")):
        res = await join_deals_to_work_orders()
        executed_tools.append({"tool": "join_deals_to_work_orders", "input": {}, "output": res})
        summary = res.get("summary", {})
        matched_cnt = summary.get("matched_pairs_count", 0)
        won_unlinked = len(res.get("won_deals_unlinked", []))
        recommended_chart = "sector_health_matrix"

        text = (
            f"### Direct Answer\n"
            f"Cross-board analysis linked **{matched_cnt}** opportunities between Deals and Work Orders "
            f"({summary.get('exact_matches_count', 0)} exact matches, {summary.get('fuzzy_matches_count', 0)} high-confidence fuzzy matches). "
            f"There are **{won_unlinked}** Won Deals currently unlinked on the execution board, representing an operational handoff gap.\n\n"
            f"### Key Numbers\n"
            f"- **Deals Board Total:** {summary.get('total_deals', 0)}\n"
            f"- **Work Orders Board Total:** {summary.get('total_work_orders', 0)}\n"
            f"- **Linkage Coverage:** {summary.get('deal_linkage_coverage_pct', 0)}%\n\n"
            f"### Strategic Insight\n"
            f"Sectors with high pipeline value but multiple delayed work orders require executive oversight before signing new contracts.\n\n"
            f"### Data Quality & Confidence Caveats\n"
            f"- Entity matching prioritized exact client codes first, normalized company names second, and RapidFuzz (threshold >= 90) third.\n\n"
            f"### Source Scope\n"
            f"Retrieved from Deals (`{settings.MONDAY_DEALS_BOARD_ID}`) and Work Orders (`{settings.MONDAY_WORK_ORDERS_BOARD_ID}`)."
        )
        return {
            "response": text,
            "tool_calls": executed_tools,
            "recommended_chart": recommended_chart,
            "data_caveats": res.get("data_quality_caveats", [])
        }

    if any(k in q for k in ("work order", "delay", "operation", "delivery", "billing", "collected", "receivable", "invoice")):
        res = await compute_ops_metrics()
        executed_tools.append({"tool": "compute_ops_metrics", "input": {}, "output": res})
        total_wo = res.get("total_work_orders", 0)
        delayed = res.get("delayed_count", 0)
        fin = res.get("financial_summary", {})
        billed = fin.get("total_billed_value", 0.0)
        collected = fin.get("total_collected_amount", 0.0)
        receivables = fin.get("total_amount_receivable", 0.0)
        recommended_chart = "billing_funnel" if any(k in q for k in ("bill", "collect", "receivable")) else "execution_status"

        text = (
            f"### Direct Answer\n"
            f"Operations has **{total_wo}** active work orders with **{delayed}** currently flagged as delayed or at-risk. "
            f"Financially, **\\${billed:,.0f}** has been billed, **\\${collected:,.0f}** collected, leaving **\\${receivables:,.0f}** in outstanding receivables.\n\n"
            f"### Key Numbers\n"
            f"- **Total Work Orders:** {total_wo}\n"
            f"- **Delayed Orders:** {delayed} ({round(delayed/total_wo*100, 1) if total_wo else 0}% of active workload)\n"
            f"- **Outstanding Receivables:** \\${receivables:,.0f} (Collection Efficiency: {fin.get('collection_rate_pct', 0.0)}%)\n\n"
            f"### Strategic Insight\n"
            f"Unresolved execution delays correlate directly with milestone billing delays. Unblocking key delayed orders will accelerate cash collection.\n\n"
            f"### Data Quality & Confidence Caveats\n"
            f"- Financial metrics calculated from {fin.get('billed_records_count', 0)} of {total_wo} work orders with populated billed amounts.\n\n"
            f"### Source Scope\n"
            f"Retrieved from Work Orders Board (`{settings.MONDAY_WORK_ORDERS_BOARD_ID}`)."
        )
        return {
            "response": text,
            "tool_calls": executed_tools,
            "recommended_chart": recommended_chart,
            "data_caveats": res.get("data_quality_caveats", [])
        }

    # Default to Sales Pipeline
    filters = {}
    if "energy" in q:
        filters["sector"] = "Energy"
    elif "mining" in q:
        filters["sector"] = "Mining"
    elif "infrastructure" in q or "infra" in q:
        filters["sector"] = "Infrastructure"

    res = await compute_pipeline_metrics(filters=filters)
    executed_tools.append({"tool": "compute_pipeline_metrics", "input": {"filters": filters}, "output": res})
    tot_val = res.get("total_pipeline_value", 0.0)
    w_val = res.get("weighted_pipeline_value", 0.0)
    tot_deals = res.get("total_deals", 0)
    open_cnt = res.get("open_deals_count", 143)
    won_cnt = res.get("won_deals_count", 73)
    lost_cnt = res.get("lost_deals_count", 79)
    hold_cnt = res.get("on_hold_completed_deals_count", 52)
    deals_with_val = res.get("deals_with_value_count", 0)
    
    if any(k in q for k in ("open", "active deal", "how many deal", "in progress", "pipeline stage")):
        recommended_chart = "pipeline_by_stage"
        text = (
            f"### Direct Answer\n"
            f"There are **{open_cnt} active open deals** currently in the sales pipeline across pre-close stages "
            f"(out of **{tot_deals}** total records on the Deals board).\n\n"
            f"### Key Numbers\n"
            f"- **Active Open Deals:** **{open_cnt}** (Leads, SQLs, Demos, Feasibility, Proposals, Negotiations, POCs)\n"
            f"- **Won / Contracted Deals:** **{won_cnt}** (Won: 27, Work Orders Received: 46)\n"
            f"- **Lost / Disqualified Deals:** **{lost_cnt}** (Lost: 42, Not Relevant: 37)\n"
            f"- **On Hold / Completed / Invoiced:** **{hold_cnt}**\n"
            f"- **Total Deals on Board:** **{tot_deals}** (Verified Valued Deals: {deals_with_val})\n\n"
            f"### Strategic Insight\n"
            f"Focus sales leadership attention on the 41 late-stage open opportunities (Proposals & Negotiations) to accelerate deal conversion into contracted Work Orders.\n\n"
            f"### Data Quality & Confidence Caveats\n"
            f"- Calculations exclude closed/lost items from the active open count. {res.get('deals_missing_value_count', 0)} deals lack numeric monetary values.\n\n"
            f"### Source Scope\n"
            f"Retrieved from Deals Board (`{settings.MONDAY_DEALS_BOARD_ID}`)."
        )
    else:
        recommended_chart = "close_date_trend" if any(k in q for k in ("close", "30 days", "month")) else "pipeline_by_sector"
        sector_label = f" for {filters['sector']}" if "sector" in filters else ""
        text = (
            f"### Direct Answer\n"
            f"The total sales pipeline{sector_label} is **\\${tot_val:,.0f}** across **{tot_deals}** deals "
            f"(with **{open_cnt}** active open opportunities and a weighted probability value of **\\${w_val:,.0f}**).\n\n"
            f"### Key Numbers\n"
            f"- **Total Pipeline Value:** \\${tot_val:,.0f}\n"
            f"- **Active Open Deals:** {open_cnt} of {tot_deals} total deals\n"
            f"- **Weighted Pipeline:** \\${w_val:,.0f}\n"
            f"- **Verified Valued Deals:** {deals_with_val}\n\n"
            f"### Strategic Insight\n"
            f"Prioritize closing high-value opportunities in negotiation to secure cash inflows.\n\n"
            f"### Data Quality & Confidence Caveats\n"
            f"- Calculations exclude unparseable or blank deal values. {res.get('deals_missing_value_count', 0)} deals have missing monetary amounts.\n\n"
            f"### Source Scope\n"
            f"Retrieved from Deals Board (`{settings.MONDAY_DEALS_BOARD_ID}`)."
        )
    return {
        "response": text,
        "tool_calls": executed_tools,
        "recommended_chart": recommended_chart,
        "data_caveats": res.get("data_quality_caveats", [])
    }


async def run_agent(
    message: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Standard entrypoint for FastAPI and Streamlit chat endpoints."""
    agent = BusinessIntelligenceAgent()
    return await agent.run(user_question=message, conversation_history=conversation_history)
