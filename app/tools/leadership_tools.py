"""Leadership summary generator producing 8-section executive briefings."""

from __future__ import annotations

import datetime
from typing import Any, Dict, Optional
from app.tools.deals_tools import compute_pipeline_metrics
from app.tools.work_order_tools import compute_ops_metrics
from app.tools.join_tools import join_deals_to_work_orders


async def generate_leadership_summary(
    topic: Optional[str] = None,
    period: Optional[str] = None
) -> Dict[str, Any]:
    """Generate structured 8-section executive BI briefing from live Monday.com data."""
    topic_str = topic or "Executive Business Review"
    period_str = period or datetime.date.today().strftime("%B %Y")
    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Fetch live deterministic metrics
    deals_metrics = await compute_pipeline_metrics()
    ops_metrics = await compute_ops_metrics()
    join_metrics = await join_deals_to_work_orders()

    total_pipeline = deals_metrics.get("total_pipeline_value", 0.0)
    weighted_pipeline = deals_metrics.get("weighted_pipeline_value", 0.0)
    total_deals = deals_metrics.get("total_deals", 0)
    deals_with_val = deals_metrics.get("deals_with_value_count", 0)
    top_3_pct = deals_metrics.get("concentration_risk", {}).get("top_3_pct", 0.0)
    win_rate = deals_metrics.get("win_rate_pct")
    top_deals = deals_metrics.get("top_opportunities", [])[:3]

    total_wos = ops_metrics.get("total_work_orders", 0)
    delayed_wos = ops_metrics.get("delayed_count", 0)
    fin = ops_metrics.get("financial_summary", {})
    billed_val = fin.get("total_billed_value", 0.0)
    collected_val = fin.get("total_collected_amount", 0.0)
    receivables_val = fin.get("total_amount_receivable", 0.0)

    # Sector highlight
    sectors = deals_metrics.get("pipeline_by_sector", {})
    top_sector = max(sectors.items(), key=lambda x: x[1].get("total_value", 0), default=("None", {}))
    top_sec_name = top_sector[0]
    top_sec_val = top_sector[1].get("total_value", 0.0)

    # Build Markdown Brief
    md_lines = [
        f"# 📋 Executive Leadership BI Brief: {topic_str}",
        f"**Period:** {period_str} | **Generated:** {generated_at} | **Source:** Live Monday.com Data",
        "",
        "---",
        "",
        "## 1. Executive Takeaway",
        f"Active sales pipeline stands at **${total_pipeline:,.0f}** across **{total_deals}** opportunities (weighted: **${weighted_pipeline:,.0f}**). "
        f"**{top_sec_name}** represents the largest revenue driver (${top_sec_val:,.0f}). "
        f"On execution, **{delayed_wos}** of **{total_wos}** work orders are experiencing delays, while total outstanding receivables sit at **${receivables_val:,.0f}**.",
        "",
        "## 2. Sales Pipeline Health",
        f"- **Total Pipeline Value:** ${total_pipeline:,.0f} ({deals_with_val}/{total_deals} deals with verified valuation)",
        f"- **Weighted Pipeline:** ${weighted_pipeline:,.0f} (factoring close probabilities)",
        f"- **Historical Win Rate:** {f'{win_rate}%' if win_rate is not None else 'N/A'}",
        f"- **Concentration Risk:** Top 3 deals account for **{top_3_pct}%** of total pipeline value.",
        "",
        "## 3. Largest High-Value Opportunities",
    ]

    for d in top_deals:
        val_str = f"${d['deal_value']:,.0f}" if d.get("deal_value") else "Unspecified"
        prob_str = f"{d['closure_probability']}%" if d.get("closure_probability") is not None else "N/A"
        md_lines.append(f"- **{d['deal_name']}** ({d['sector']}) — Value: **{val_str}** | Stage: `{d['stage']}` | Prob: {prob_str} | Close: {d.get('close_date', 'TBD')}")

    md_lines.extend([
        "",
        "## 4. Sector Performance & Concentration",
        f"Revenue opportunity is concentrated in **{top_sec_name}** (${top_sec_val:,.0f}).",
    ])

    for s_name, s_data in list(sectors.items())[:4]:
        md_lines.append(f"- **{s_name}:** ${s_data.get('total_value', 0):,.0f} ({s_data.get('deal_count', 0)} deals, {s_data.get('pct_of_pipeline', 0)}% share)")

    md_lines.extend([
        "",
        "## 5. Operational & Execution Health",
        f"- **Active Work Orders:** {total_wos}",
        f"- **Delayed / At-Risk Orders:** **{delayed_wos}** orders requiring operational intervention.",
        f"- **On-Time Delivery Rate:** {ops_metrics.get('on_time_delivery_pct', 'N/A')}%",
        "",
        "## 6. Billing & Collection Position",
        f"- **Total Billed Value:** ${billed_val:,.0f}",
        f"- **Total Collected Amount:** ${collected_val:,.0f}",
        f"- **Outstanding Receivables:** **${receivables_val:,.0f}**",
        f"- **Collection Efficiency:** {fin.get('collection_rate_pct', 0.0)}%",
        "",
        "## 7. Key Founder-Level Risks",
        f"1. **Pipeline Concentration:** High dependency on top {top_3_pct}% opportunities.",
        f"2. **Operational Backlog:** {delayed_wos} projects delayed, creating delivery and milestone payment risk.",
        f"3. **Receivables Aging:** ${receivables_val:,.0f} uncollected balance across execution milestones.",
        "",
        "## 8. Recommended Actions & Data Quality Caveats",
        "**Strategic Actions:**",
        "1. Prioritize executive sponsorship for the top 3 high-value pipeline deals.",
        "2. Unblock stalled work orders in delayed sectors to release pending milestone billing.",
        "3. Audit customer accounts with large unpaid receivables.",
        "",
        "**Data Quality & Confidence Limitations:**",
    ])

    all_caveats = (
        deals_metrics.get("data_quality_caveats", []) +
        ops_metrics.get("data_quality_caveats", []) +
        join_metrics.get("data_quality_caveats", [])
    )
    for cav in all_caveats:
        md_lines.append(f"- *{cav}*")

    full_markdown = "\n".join(md_lines)

    return {
        "headline": f"Leadership Brief: Pipeline ${total_pipeline:,.0f} | Delays {delayed_wos}/{total_wos} | Receivables ${receivables_val:,.0f}",
        "topic": topic_str,
        "period": period_str,
        "generated_at": generated_at,
        "markdown_summary": full_markdown,
        "metrics_summary": {
            "total_pipeline": total_pipeline,
            "weighted_pipeline": weighted_pipeline,
            "delayed_work_orders": delayed_wos,
            "receivables": receivables_val
        }
    }
