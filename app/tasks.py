"""Celery and Background Tasks for Board Extraction and Pre-computation (§3)."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.celery_app import celery_app
from app.config import settings
from app.tools.monday_client import monday_client
from app.tools.deals_tools import get_deals, compute_pipeline_metrics
from app.tools.work_order_tools import get_work_orders, compute_ops_metrics
from app.tools.join_tools import join_deals_to_work_orders
from app.cache import set_cached_metrics

logger = logging.getLogger("app.tasks")


async def execute_board_refresh_workflow() -> Dict[str, Any]:
    """Async execution of full board refresh and metric pre-computation."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    logger.info(f"Starting background board refresh workflow at {now_str}...")

    # 1. Fetch both boards concurrently without cache
    deals_id = settings.MONDAY_DEALS_BOARD_ID
    wo_id = settings.MONDAY_WORK_ORDERS_BOARD_ID

    boards_data = await monday_client.fetch_all_boards([deals_id, wo_id], use_cache=False)
    deals_items = boards_data.get(str(deals_id), {}).get("items", [])
    wo_items = boards_data.get(str(wo_id), {}).get("items", [])

    # 2. Pre-compute analytics
    d_metrics = await compute_pipeline_metrics()
    w_metrics = await compute_ops_metrics()
    j_metrics = await join_deals_to_work_orders()

    # 3. Cache pre-computed metrics
    await set_cached_metrics("deals_analytics", d_metrics)
    await set_cached_metrics("work_orders_analytics", w_metrics)
    await set_cached_metrics("cross_board_analytics", j_metrics)

    summary = {
        "status": "success",
        "refreshed_at": now_str,
        "deals_retrieved": len(deals_items),
        "work_orders_retrieved": len(wo_items),
        "total_pipeline_value": d_metrics.get("total_pipeline_value", 0.0),
        "outstanding_receivables": w_metrics.get("financial_summary", {}).get("total_amount_receivable", 0.0)
    }
    logger.info(f"Completed background board refresh workflow: {summary}")
    return summary


@celery_app.task(name="app.tasks.refresh_all_boards_task")
def refresh_all_boards_task() -> Dict[str, Any]:
    """Celery task entrypoint for scheduled background extraction."""
    return asyncio.run(execute_board_refresh_workflow())
