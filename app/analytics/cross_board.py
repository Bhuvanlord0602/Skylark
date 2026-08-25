"""Deterministic Cross-Board Analytics Engine.

Combines Deals (Sales Pipeline) and Work Orders (Operations) to generate:
1. ⭐ Sector Health Matrix (Opportunity vs. Execution vs. Receivables)
2. Pipeline vs. Operational Load scatter data
3. Sales-to-Ops Handoff Linkage & Execution Gaps
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from collections import defaultdict


def compute_cross_board_analytics(
    deals_metrics: Dict[str, Any],
    ops_metrics: Dict[str, Any],
    join_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Combine Deals, Work Orders, and Join Results into unified executive intelligence."""
    sector_pipeline = deals_metrics.get("pipeline_by_sector", {})
    wo_by_sector = ops_metrics.get("work_orders_by_sector", {})
    delayed_by_sector = ops_metrics.get("delayed_by_sector", {})

    all_sectors = sorted(list(set(list(sector_pipeline.keys()) + list(wo_by_sector.keys()))))

    # 1. Sector Health Matrix
    sector_health_matrix: List[Dict[str, Any]] = []
    for sec in all_sectors:
        sec_deal_info = sector_pipeline.get(sec, {})
        pipe_val = sec_deal_info.get("total_value", 0.0)
        d_cnt = sec_deal_info.get("deal_count", 0)
        wo_cnt = wo_by_sector.get(sec, 0)
        del_cnt = delayed_by_sector.get(sec, 0)

        # Assess execution risk
        if wo_cnt > 0:
            delay_pct = (del_cnt / wo_cnt) * 100
            if delay_pct >= 25.0:
                risk_level = "High Risk"
            elif delay_pct > 0.0:
                risk_level = "Moderate Risk"
            else:
                risk_level = "Healthy"
        else:
            delay_pct = 0.0
            risk_level = "No Active Ops" if pipe_val > 0 else "Low"

        sector_health_matrix.append({
            "sector": sec,
            "pipeline_value": pipe_val,
            "deal_count": d_cnt,
            "work_order_count": wo_cnt,
            "delayed_work_orders": del_cnt,
            "delay_pct": round(delay_pct, 1),
            "execution_risk": risk_level,
            "avg_deal_size": sec_deal_info.get("avg_deal_size", 0.0),
            "win_rate_pct": sec_deal_info.get("win_rate_pct")
        })

    # Sort sector health matrix by pipeline value descending
    sector_health_matrix.sort(key=lambda x: x["pipeline_value"], reverse=True)

    # 2. Pipeline vs Operational Load Scatter Data
    scatter_data = [
        {
            "sector": item["sector"],
            "pipeline_value": item["pipeline_value"],
            "work_order_count": item["work_order_count"],
            "delayed_count": item["delayed_work_orders"],
            "execution_risk": item["execution_risk"]
        }
        for item in sector_health_matrix
        if item["pipeline_value"] > 0 or item["work_order_count"] > 0
    ]

    # 3. Sales-to-Ops Handoff & Execution Gaps
    matched_records = join_results.get("matched_records", [])
    unmatched_deals = join_results.get("unmatched_deals", [])
    unmatched_wos = join_results.get("unmatched_work_orders", [])
    join_summary = join_results.get("summary", {})

    won_deals_unlinked = [
        d for d in unmatched_deals
        if "won" in str(d.get("stage", "")).lower()
    ]

    return {
        "sector_health_matrix": sector_health_matrix,
        "pipeline_vs_ops_scatter": scatter_data,
        "join_summary": join_summary,
        "matched_pairs_count": len(matched_records),
        "unmatched_deals_count": len(unmatched_deals),
        "unmatched_work_orders_count": len(unmatched_wos),
        "won_deals_unlinked_count": len(won_deals_unlinked),
        "won_deals_unlinked": won_deals_unlinked[:10],
        "cross_board_caveats": [
            f"Cross-board analysis matched {len(matched_records)} deal-to-work-order pairs ({join_summary.get('exact_matches_count', 0)} exact, {join_summary.get('fuzzy_matches_count', 0)} high-confidence fuzzy).",
            f"{len(won_deals_unlinked)} Won Deals have no linked Work Orders currently on the execution board."
        ] if len(won_deals_unlinked) > 0 else [
            f"Cross-board analysis matched {len(matched_records)} deal-to-work-order pairs."
        ]
    }

