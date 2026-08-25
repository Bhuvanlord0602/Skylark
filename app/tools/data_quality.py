"""Data Quality and Audit report generation tool."""

from __future__ import annotations

import logging
from typing import Any, Dict
from app.tools.deals_tools import get_deals
from app.tools.work_order_tools import get_work_orders
from app.tools.join_tools import join_deals_to_work_orders
from app.config import settings

logger = logging.getLogger("data_quality")


async def data_quality_report() -> Dict[str, Any]:
    """Generate comprehensive Data Quality & Audit report across Deals, Work Orders, and Join linkage."""
    deals_res = await get_deals()
    wo_res = await get_work_orders()
    join_res = await join_deals_to_work_orders()

    deals_quality = deals_res.get("data_quality", {})
    wo_quality = wo_res.get("data_quality", {})
    join_summary = join_res.get("summary", {})

    total_deals = deals_res.get("total_retrieved", 0)
    total_orders = wo_res.get("total_retrieved", 0)

    deals_field_audit = deals_quality.get("field_audit", {})
    deals_missing_val = deals_field_audit.get("deal_value", {}).get("missing", 0)
    deals_val_missing_pct = round((deals_missing_val / total_deals * 100), 1) if total_deals > 0 else 0.0

    notes = [
        f"{deals_val_missing_pct}% of deals do not have a usable deal value.",
        "Several close dates are missing or marked TBD.",
        "Pipeline calculations exclude records with unparseable or missing monetary values.",
        f"Entity matching linked {join_summary.get('matched_pairs_count', 0)} opportunities between Deals and Work Orders."
    ]

    return {
        "status": "success",
        "deals_board": {
            "board_id": settings.MONDAY_DEALS_BOARD_ID,
            "total_items": total_deals,
            "score_breakdown": deals_quality.get("score_breakdown", {}),
            "field_audit": deals_field_audit
        },
        "work_orders_board": {
            "board_id": settings.MONDAY_WORK_ORDERS_BOARD_ID,
            "total_items": total_orders,
            "score_breakdown": wo_quality.get("score_breakdown", {}),
            "field_audit": wo_quality.get("field_audit", {})
        },
        "cross_board_join": join_summary,
        "data_quality_notes": notes
    }
