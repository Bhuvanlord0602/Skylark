"""Multi-phase cross-board entity matcher connecting Deals and Work Orders.

Matching Priority:
- Level 1: Exact Match (Client Code / Customer Code / Explicit Reference ID)
- Level 2: Normalized Client Name exact match (corporate suffixes stripped)
- Level 3: Cautious Fuzzy Match via RapidFuzz token_sort_ratio (Threshold >= 90)

Invariant: Never silently drop unmatched records; never treat fuzzy match as certain.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from rapidfuzz import fuzz

from app.tools.deals_tools import get_deals, compute_pipeline_metrics
from app.tools.work_order_tools import get_work_orders, compute_ops_metrics
from app.analytics.deals_metrics import compute_deals_analytics
from app.analytics.work_orders_metrics import compute_work_orders_analytics
from app.analytics.cross_board import compute_cross_board_analytics

logger = logging.getLogger("join_tools")


async def join_deals_to_work_orders(
    deals_filters: Optional[Dict[str, Any]] = None,
    work_orders_filters: Optional[Dict[str, Any]] = None,
    fuzzy_threshold: float = 90.0
) -> Dict[str, Any]:
    """Perform deterministic multi-phase join between Deals and Work Orders."""
    deals_res = await get_deals(deals_filters)
    orders_res = await get_work_orders(work_orders_filters)

    deals: List[Dict[str, Any]] = deals_res.get("deals", [])
    work_orders: List[Dict[str, Any]] = orders_res.get("work_orders", [])

    matched_records: List[Dict[str, Any]] = []
    unmatched_deals: List[Dict[str, Any]] = []
    unmatched_work_orders: List[Dict[str, Any]] = []

    matched_deal_ids = set()
    matched_wo_ids = set()

    # --- Phase 1: Level 1 - Explicit Code / Customer Code Exact Match ---
    wo_by_code: Dict[str, List[Dict[str, Any]]] = {}
    for wo in work_orders:
        code = wo.get("customer_name_code")
        if code and str(code).strip():
            code_clean = str(code).strip().lower()
            if code_clean not in wo_by_code:
                wo_by_code[code_clean] = []
            wo_by_code[code_clean].append(wo)

    for deal in deals:
        d_code = deal.get("client_code")
        if d_code and str(d_code).strip():
            d_code_clean = str(d_code).strip().lower()
            if d_code_clean in wo_by_code:
                for matched_wo in wo_by_code[d_code_clean]:
                    matched_records.append({
                        "deal_id": deal["id"],
                        "deal_name": deal["deal_name"],
                        "work_order_id": matched_wo["id"],
                        "work_order_name": matched_wo["deal_name"],
                        "client": deal["client"],
                        "sector": deal["sector"],
                        "deal_value": deal.get("deal_value"),
                        "deal_stage": deal.get("stage"),
                        "wo_status": matched_wo.get("execution_status"),
                        "billed_value": matched_wo.get("billed_value"),
                        "amount_receivable": matched_wo.get("amount_receivable"),
                        "match_type": "exact_code",
                        "match_confidence": 1.0,
                        "match_score": 100.0
                    })
                    matched_wo_ids.add(matched_wo["id"])
                matched_deal_ids.add(deal["id"])

    # --- Phase 2: Level 2 - Normalized Client Name Exact Match ---
    wo_by_norm_client: Dict[str, List[Dict[str, Any]]] = {}
    for wo in work_orders:
        if wo["id"] in matched_wo_ids:
            continue
        norm_name = wo.get("client_normalized")
        if norm_name:
            if norm_name not in wo_by_norm_client:
                wo_by_norm_client[norm_name] = []
            wo_by_norm_client[norm_name].append(wo)

    for deal in deals:
        if deal["id"] in matched_deal_ids:
            continue
        deal_norm = deal.get("client_normalized")
        if not deal_norm:
            continue

        if deal_norm in wo_by_norm_client:
            for matched_wo in wo_by_norm_client[deal_norm]:
                matched_records.append({
                    "deal_id": deal["id"],
                    "deal_name": deal["deal_name"],
                    "work_order_id": matched_wo["id"],
                    "work_order_name": matched_wo["deal_name"],
                    "client": deal["client"],
                    "sector": deal["sector"],
                    "deal_value": deal.get("deal_value"),
                    "deal_stage": deal.get("stage"),
                    "wo_status": matched_wo.get("execution_status"),
                    "billed_value": matched_wo.get("billed_value"),
                    "amount_receivable": matched_wo.get("amount_receivable"),
                    "match_type": "exact_normalized_client",
                    "match_confidence": 0.95,
                    "match_score": 100.0
                })
                matched_wo_ids.add(matched_wo["id"])
            matched_deal_ids.add(deal["id"])

    # --- Phase 3: Level 3 - Cautious Fuzzy Match (RapidFuzz >= 90) ---
    remaining_deals = [d for d in deals if d["id"] not in matched_deal_ids and d.get("client_normalized")]
    remaining_wos = [w for w in work_orders if w["id"] not in matched_wo_ids and w.get("client_normalized")]

    for deal in remaining_deals:
        deal_norm = deal["client_normalized"]
        best_score = 0.0
        best_wo = None

        for wo in remaining_wos:
            wo_norm = wo["client_normalized"]
            score = float(fuzz.token_sort_ratio(deal_norm, wo_norm))
            if score > best_score:
                best_score = score
                best_wo = wo

        if best_score >= fuzzy_threshold and best_wo is not None:
            matched_records.append({
                "deal_id": deal["id"],
                "deal_name": deal["deal_name"],
                "work_order_id": best_wo["id"],
                "work_order_name": best_wo["deal_name"],
                "client": f"{deal['client']} ~ {best_wo['client']}",
                "sector": deal["sector"],
                "deal_value": deal.get("deal_value"),
                "deal_stage": deal.get("stage"),
                "wo_status": best_wo.get("execution_status"),
                "billed_value": best_wo.get("billed_value"),
                "amount_receivable": best_wo.get("amount_receivable"),
                "match_type": "fuzzy_rapidfuzz",
                "match_confidence": round(best_score / 100.0, 2),
                "match_score": round(best_score, 1)
            })
            matched_deal_ids.add(deal["id"])
            matched_wo_ids.add(best_wo["id"])

    # --- Phase 4: Identify Unmatched Records ---
    for deal in deals:
        if deal["id"] not in matched_deal_ids:
            unmatched_deals.append(deal)

    for wo in work_orders:
        if wo["id"] not in matched_wo_ids:
            unmatched_work_orders.append(wo)

    # Compute overall summary
    exact_count = sum(1 for m in matched_records if "exact" in m["match_type"])
    fuzzy_count = sum(1 for m in matched_records if m["match_type"] == "fuzzy_rapidfuzz")
    total_deals_count = len(deals)
    coverage_pct = round((len(matched_deal_ids) / total_deals_count * 100), 1) if total_deals_count > 0 else 0.0

    join_summary = {
        "total_deals": total_deals_count,
        "total_work_orders": len(work_orders),
        "matched_pairs_count": len(matched_records),
        "exact_matches_count": exact_count,
        "fuzzy_matches_count": fuzzy_count,
        "unmatched_deals_count": len(unmatched_deals),
        "unmatched_work_orders_count": len(unmatched_work_orders),
        "deal_linkage_coverage_pct": coverage_pct
    }

    # Cross-Board Intelligence Calculations
    deals_metrics = compute_deals_analytics(deals, deals_res.get("total_retrieved", len(deals)))
    ops_metrics = compute_work_orders_analytics(work_orders, orders_res.get("total_retrieved", len(work_orders)))
    cross_analytics = compute_cross_board_analytics(
        deals_metrics,
        ops_metrics,
        {
            "matched_records": matched_records,
            "unmatched_deals": unmatched_deals,
            "unmatched_work_orders": unmatched_work_orders,
            "summary": join_summary
        }
    )

    return {
        "matched_records": matched_records,
        "unmatched_deals": unmatched_deals,
        "unmatched_work_orders": unmatched_work_orders,
        "summary": join_summary,
        "sector_health_matrix": cross_analytics.get("sector_health_matrix", []),
        "pipeline_vs_ops_scatter": cross_analytics.get("pipeline_vs_ops_scatter", []),
        "won_deals_unlinked": cross_analytics.get("won_deals_unlinked", []),
        "data_quality_caveats": cross_analytics.get("cross_board_caveats", [])
    }
