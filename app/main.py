"""FastAPI Backend Server for Monday.com Executive BI Agent.

Features:
- Live, strictly read-only Monday.com GraphQL integration
- Multi-tier Redis and in-memory caching (§2)
- Session conversation memory (§2.2)
- Background board refresh loop & on-demand POST /refresh endpoint (§3)
- Deterministic analytics and interactive chart generation
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.tools.monday_client import monday_client
from app.tools.column_map import build_dynamic_column_map_with_metadata, DEALS_COLUMN_MAP, WORK_ORDERS_COLUMN_MAP
from app.tools.deals_tools import get_deals, compute_pipeline_metrics
from app.tools.work_order_tools import get_work_orders, compute_ops_metrics
from app.tools.join_tools import join_deals_to_work_orders
from app.tools.leadership_tools import generate_leadership_summary
from app.tools.provenance_tools import get_metric_provenance
from app.cache import get_cache_status, clear_board_cache
from app.memory import get_session_history, append_session_turn, get_memory_stats
from app.tasks import execute_board_refresh_workflow
from app.agent import run_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("api")

from contextlib import asynccontextmanager

# --- Background Polling Loop (§3.2) ---
async def background_polling_loop():
    """Periodic in-process background task ensuring fresh board snapshots."""
    logger.info("Initializing in-process background board refresh loop...")
    # Initial warm-up on startup
    try:
        await execute_board_refresh_workflow()
    except Exception as e:
        logger.warning(f"Initial cache warm-up encountered error: {e}")

    while True:
        try:
            await asyncio.sleep(settings.BACKGROUND_REFRESH_INTERVAL_SECONDS)
            logger.info(f"Running periodic background board refresh (every {settings.BACKGROUND_REFRESH_INTERVAL_SECONDS}s)...")
            await execute_board_refresh_workflow()
        except asyncio.CancelledError:
            logger.info("Background refresh loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in background refresh cycle: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown lifecycle management."""
    task = None
    if settings.ENABLE_BACKGROUND_REFRESH:
        task = asyncio.create_task(background_polling_loop())
    yield
    if task:
        task.cancel()


app = FastAPI(
    title="Skylark Drones — Monday.com Executive BI Agent API",
    description="Conversational BI Agent with deterministic metrics, caching, and live read-only Monday.com integration.",
    version="2.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., description="Executive question or query")
    session_id: Optional[str] = Field(default=None, description="Optional session identifier for conversation memory")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional explicit history override")


class LeadershipSummaryRequest(BaseModel):
    topic: Optional[str] = Field(default="Executive Business Review", description="Topic for leadership summary")
    period: Optional[str] = Field(default=None, description="Time period (e.g. Q3 2025)")


# --- API Routes ---

@app.get("/")
async def root():
    """Service metadata, caching, and health status entrypoint."""
    return {
        "service": "Skylark Drones Monday.com Executive BI Agent",
        "status": "online",
        "version": "2.2.0",
        "llm_provider": "groq",
        "model_configured": settings.GROQ_MODEL,
        "boards_configured": {
            "deals_board_id": settings.MONDAY_DEALS_BOARD_ID,
            "work_orders_board_id": settings.MONDAY_WORK_ORDERS_BOARD_ID
        },
        "cache": get_cache_status(),
        "memory": get_memory_stats()
    }


@app.get("/health")
async def health():
    """Live connectivity and item count health check for Monday.com boards and Groq LLM."""
    try:
        health_data = await monday_client.health_check()
        health_data["llm_provider"] = "groq"
        health_data["model_configured"] = settings.GROQ_MODEL
        health_data["monday_configured"] = bool(settings.MONDAY_API_TOKEN)
        return health_data
    except Exception as e:
        logger.error(f"Health check exception: {e}")
        return {
            "status": "unhealthy",
            "api_reachable": False,
            "llm_provider": "groq",
            "monday_configured": bool(settings.MONDAY_API_TOKEN),
            "error": str(e)
        }


@app.post("/refresh")
async def refresh_boards(background_tasks: BackgroundTasks):
    """Trigger an immediate asynchronous refresh of both Monday.com boards (§3)."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    background_tasks.add_task(execute_board_refresh_workflow)
    return {
        "status": "refresh_initiated",
        "message": "Background extraction and metric pre-computation started.",
        "requested_at": now_iso
    }


@app.get("/schema")
async def schema():
    """Inspect active dynamic column mappings and confidence metadata for both boards."""
    deals_meta, wo_meta = [], []
    deals_map, wo_map = DEALS_COLUMN_MAP, WORK_ORDERS_COLUMN_MAP

    try:
        deals_schema = await monday_client.fetch_board_schema(settings.MONDAY_DEALS_BOARD_ID)
        deals_map, deals_meta = build_dynamic_column_map_with_metadata(deals_schema.get("columns", []), "deals")
    except Exception as e:
        logger.warning(f"Using static deals schema: {e}")

    try:
        wo_schema = await monday_client.fetch_board_schema(settings.MONDAY_WORK_ORDERS_BOARD_ID)
        wo_map, wo_meta = build_dynamic_column_map_with_metadata(wo_schema.get("columns", []), "work_orders")
    except Exception as e:
        logger.warning(f"Using static work orders schema: {e}")

    return {
        "deals_column_map": deals_map,
        "deals_mapping_metadata": deals_meta,
        "work_orders_column_map": wo_map,
        "work_orders_mapping_metadata": wo_meta
    }


@app.get("/data-quality")
async def data_quality():
    """Retrieve comprehensive data quality report across both boards and cross-board join."""
    deals_res = await get_deals()
    wo_res = await get_work_orders()
    join_res = await join_deals_to_work_orders()

    deals_quality = deals_res.get("data_quality", {})
    wo_quality = wo_res.get("data_quality", {})
    join_summary = join_res.get("summary", {})

    return {
        "deals_board": {
            "board_id": settings.MONDAY_DEALS_BOARD_ID,
            "total_items": deals_res.get("total_retrieved", 0),
            "score_breakdown": deals_quality.get("score_breakdown", {}),
            "field_audit": deals_quality.get("field_audit", {})
        },
        "work_orders_board": {
            "board_id": settings.MONDAY_WORK_ORDERS_BOARD_ID,
            "total_items": wo_res.get("total_retrieved", 0),
            "score_breakdown": wo_quality.get("score_breakdown", {}),
            "field_audit": wo_quality.get("field_audit", {})
        },
        "cross_board_join": join_summary
    }


@app.get("/analytics/deals")
async def analytics_deals():
    """Retrieve complete deals pipeline analytics."""
    return await compute_pipeline_metrics()


@app.get("/analytics/work-orders")
async def analytics_work_orders():
    """Retrieve complete work orders operational and financial analytics."""
    return await compute_ops_metrics()


@app.get("/analytics/cross-board")
async def analytics_cross_board():
    """Retrieve complete cross-board Sector Health Matrix and entity matching analytics."""
    return await join_deals_to_work_orders()


@app.get("/provenance/{metric_name}")
async def metric_provenance(metric_name: str):
    """Explain calculation provenance and data lineage for a metric ('Why this number?')."""
    return await get_metric_provenance(metric_name)


@app.get("/cache/status")
async def cache_status():
    """Inspect cache health and key counts."""
    return get_cache_status()


@app.post("/cache/clear")
async def cache_clear():
    """Flush all board and metric cache keys."""
    await clear_board_cache()
    return {"status": "success", "message": "Cache flushed."}


@app.post("/chat")
async def chat(req: ChatRequest):
    """Handle conversational executive query with tool execution, memory, and chart suggestions."""
    try:
        session_id = req.session_id or "default_session"

        # 1. Load session history (§2.2)
        if req.conversation_history is not None:
            history = req.conversation_history
        else:
            history = await get_session_history(session_id)

        # 2. Append user message to history
        await append_session_turn(session_id, "user", req.message)

        # 3. Run agent with loaded context
        result = await run_agent(
            message=req.message,
            conversation_history=history
        )

        # 4. Append assistant response to history
        ans_text = result.get("response", "")
        await append_session_turn(session_id, "assistant", ans_text)

        result["session_id"] = session_id
        return result

    except Exception as e:
        logger.error(f"Chat execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.get("/chat/stream")
async def chat_stream(
    message: str = Query(..., description="User message"),
    session_id: Optional[str] = Query(None, description="Session ID")
):
    """Server-Sent Events (SSE) streaming endpoint for conversational responses."""
    async def event_generator():
        try:
            s_id = session_id or "default_session"
            history = await get_session_history(s_id)
            result = await run_agent(message=message, conversation_history=history)
            await append_session_turn(s_id, "user", message)
            await append_session_turn(s_id, "assistant", result.get("response", ""))
            
            import json
            yield {
                "event": "message",
                "data": json.dumps(result)
            }
        except Exception as e:
            import json
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }

    return EventSourceResponse(event_generator())


@app.post("/leadership-summary")
async def leadership_summary(req: LeadershipSummaryRequest):
    """Generate structured 8-section Markdown leadership brief."""
    try:
        summary = await generate_leadership_summary(topic=req.topic, period=req.period)
        return summary
    except Exception as e:
        logger.error(f"Failed to generate leadership summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Leadership summary error: {str(e)}")
