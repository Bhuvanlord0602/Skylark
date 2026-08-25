"""Deterministic Sales Pipeline Metric Engine for Deals board.

Calculates metrics strictly from validated Monday.com deal records without hallucinations.
Includes comprehensive provenance metadata for every metric.
"""

from __future__ import annotations

import statistics
import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict


def compute_deals_analytics(
    deals: List[Dict[str, Any]],
    raw_deals_count: int,
    data_quality_report: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Compute complete deterministic sales pipeline analytics from normalized deals."""
    total_deals = len(deals)
    
    if total_deals == 0:
        return {
            "total_deals": 0,
            "total_pipeline_value": 0.0,
            "weighted_pipeline_value": 0.0,
            "average_deal_value": 0.0,
            "median_deal_value": 0.0,
            "win_rate_pct": None,
            "pipeline_by_sector": {},
            "pipeline_by_stage": {},
            "pipeline_by_owner": {},
            "close_date_distribution": {},
            "top_opportunities": [],
            "concentration_risk": {"top_3_pct": 0.0, "top_5_pct": 0.0},
            "stale_deals": [],
            "calculation_coverage": {
                "total_records": raw_deals_count,
                "used_records": 0,
                "excluded_records": raw_deals_count,
                "coverage_pct": 0.0
            },
            "provenance": {}
        }

    # 1. Deals with valid non-null numeric values
    deals_with_val = [d for d in deals if d.get("deal_value") is not None]
    deals_missing_val = [d for d in deals if d.get("deal_value") is None]
    total_pipeline_val = sum(d["deal_value"] for d in deals_with_val)

    val_list = [d["deal_value"] for d in deals_with_val]
    avg_deal_val = round(statistics.mean(val_list), 2) if val_list else 0.0
    median_deal_val = round(statistics.median(val_list), 2) if val_list else 0.0

    # 2. Weighted Pipeline Calculation
    # Σ(Deal Value × Closure Probability) for records with both valid
    weighted_eligible = [
        d for d in deals
        if d.get("deal_value") is not None and d.get("closure_probability") is not None
    ]
    weighted_val = sum(
        d["deal_value"] * (d["closure_probability"] / 100.0)
        for d in weighted_eligible
    )
    weighted_excluded_cnt = total_deals - len(weighted_eligible)

    # 3. Stage Segmentations & Win Rate Computation
    open_stages = ("lead", "sales qualified", "demo", "feasibility", "proposal", "commercial", "negotiation", "poc")
    won_stages = ("won", "work order")
    lost_stages = ("lost", "not relevant")
    hold_completed_stages = ("on hold", "completed", "invoice", "accrued")

    open_deals = [d for d in deals if any(s in str(d.get("stage", "")).lower() for s in open_stages)]
    won_deals = [d for d in deals if any(s in str(d.get("stage", "")).lower() for s in won_stages)]
    lost_deals = [d for d in deals if any(s in str(d.get("stage", "")).lower() for s in lost_stages)]
    hold_deals = [d for d in deals if any(s in str(d.get("stage", "")).lower() for s in hold_completed_stages)]

    closed_deals = won_deals + lost_deals

    if len(closed_deals) > 0:
        win_rate_pct = round((len(won_deals) / len(closed_deals)) * 100, 1)
        win_rate_details = f"{len(won_deals)} won out of {len(closed_deals)} closed deals ({win_rate_pct}%)"
    else:
        win_rate_pct = None
        win_rate_details = "No closed deals (Won or Lost) in dataset"

    # 4. Pipeline by Sector
    sector_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in deals:
        sec = d.get("sector_service") or d.get("sector") or "Unspecified"
        sector_groups[sec].append(d)

    pipeline_by_sector: Dict[str, Dict[str, Any]] = {}
    for sec, sec_deals in sector_groups.items():
        s_with_val = [d for d in sec_deals if d.get("deal_value") is not None]
        s_val = sum(d["deal_value"] for d in s_with_val)
        s_won = [d for d in sec_deals if "won" in str(d.get("stage", "")).lower()]
        s_lost = [d for d in sec_deals if "lost" in str(d.get("stage", "")).lower()]
        s_closed = s_won + s_lost
        s_win_rate = round((len(s_won) / len(s_closed)) * 100, 1) if s_closed else None

        pipeline_by_sector[sec] = {
            "deal_count": len(sec_deals),
            "total_value": round(s_val, 2),
            "avg_deal_size": round(s_val / len(s_with_val), 2) if s_with_val else 0.0,
            "win_rate_pct": s_win_rate,
            "won_count": len(s_won),
            "pct_of_pipeline": round((s_val / total_pipeline_val * 100), 1) if total_pipeline_val > 0 else 0.0
        }

    # 5. Pipeline by Stage
    stage_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in deals:
        stg = d.get("stage") or "Unspecified"
        stage_groups[stg].append(d)

    pipeline_by_stage: Dict[str, Dict[str, Any]] = {}
    for stg, stg_deals in stage_groups.items():
        st_with_val = [d for d in stg_deals if d.get("deal_value") is not None]
        st_val = sum(d["deal_value"] for d in st_with_val)
        pipeline_by_stage[stg] = {
            "deal_count": len(stg_deals),
            "total_value": round(st_val, 2),
            "pct_of_deals": round((len(stg_deals) / total_deals) * 100, 1),
            "pct_of_value": round((st_val / total_pipeline_val * 100), 1) if total_pipeline_val > 0 else 0.0,
            "missing_value_count": len(stg_deals) - len(st_with_val)
        }

    # 6. Pipeline by Owner
    owner_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in deals:
        own = d.get("owner") or "Unassigned"
        owner_groups[own].append(d)

    pipeline_by_owner: Dict[str, Dict[str, Any]] = {}
    for own, own_deals in owner_groups.items():
        o_with_val = [d for d in own_deals if d.get("deal_value") is not None]
        o_val = sum(d["deal_value"] for d in o_with_val)
        o_won = [d for d in own_deals if "won" in str(d.get("stage", "")).lower()]
        o_lost = [d for d in own_deals if "lost" in str(d.get("stage", "")).lower()]
        o_closed = o_won + o_lost
        o_win_rate = round((len(o_won) / len(o_closed)) * 100, 1) if o_closed else None

        pipeline_by_owner[own] = {
            "deal_count": len(own_deals),
            "total_value": round(o_val, 2),
            "avg_deal_size": round(o_val / len(o_with_val), 2) if o_with_val else 0.0,
            "win_rate_pct": o_win_rate,
            "pct_of_pipeline": round((o_val / total_pipeline_val * 100), 1) if total_pipeline_val > 0 else 0.0
        }

    # 7. Close Date Distribution (Monthly)
    close_date_monthly: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "total_value": 0.0})
    deals_missing_close_date = 0
    for d in deals:
        c_date = d.get("close_date") or d.get("expected_close_date")
        if c_date and len(c_date) >= 7:
            month_key = c_date[:7]  # YYYY-MM
            close_date_monthly[month_key]["count"] += 1
            if d.get("deal_value") is not None:
                close_date_monthly[month_key]["total_value"] += d["deal_value"]
        else:
            deals_missing_close_date += 1

    # 8. Top Opportunities
    sorted_deals = sorted(deals_with_val, key=lambda x: x.get("deal_value", 0) or 0, reverse=True)
    top_opportunities = []
    for d in sorted_deals[:10]:
        val = d.get("deal_value", 0.0)
        prob = d.get("closure_probability") or d.get("probability")
        w_val = val * (prob / 100.0) if (val and prob is not None) else None
        top_opportunities.append({
            "id": d.get("id"),
            "deal_name": d.get("deal_name") or d.get("client"),
            "client": d.get("client"),
            "sector": d.get("sector_service") or d.get("sector"),
            "stage": d.get("stage"),
            "deal_value": val,
            "closure_probability": prob,
            "weighted_value": round(w_val, 2) if w_val is not None else None,
            "close_date": d.get("close_date") or d.get("expected_close_date"),
            "owner": d.get("owner")
        })

    # 9. Concentration Risk
    top_3_val = sum(d["deal_value"] for d in sorted_deals[:3])
    top_5_val = sum(d["deal_value"] for d in sorted_deals[:5])
    top_3_pct = round((top_3_val / total_pipeline_val * 100), 1) if total_pipeline_val > 0 else 0.0
    top_5_pct = round((top_5_val / total_pipeline_val * 100), 1) if total_pipeline_val > 0 else 0.0

    # 10. Stale / At-Risk Deals
    today_iso = datetime.date.today().strftime("%Y-%m-%d")
    stale_deals = []
    for d in deals:
        c_date = d.get("close_date") or d.get("expected_close_date")
        stg = str(d.get("stage", "")).lower()
        if stg not in ("won", "lost", "completed"):
            if c_date and c_date < today_iso:
                stale_deals.append({
                    "id": d.get("id"),
                    "deal_name": d.get("deal_name") or d.get("client"),
                    "client": d.get("client"),
                    "stage": d.get("stage"),
                    "deal_value": d.get("deal_value"),
                    "close_date": c_date,
                    "risk_reason": "Close date has already passed"
                })

    # 11. Provenance Metadata
    now_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    provenance = {
        "total_pipeline": {
            "metric": "total_pipeline",
            "value": round(total_pipeline_val, 2),
            "source_board": "Deals",
            "source_board_id": "5030842959",
            "source_fields": ["deal_value"],
            "records_total": total_deals,
            "records_used": len(deals_with_val),
            "records_excluded": len(deals_missing_val),
            "exclusion_reason": "Missing or unparseable deal value",
            "calculation_coverage_pct": round((len(deals_with_val) / total_deals * 100), 1) if total_deals > 0 else 0.0,
            "retrieved_at": now_ts
        },
        "weighted_pipeline": {
            "metric": "weighted_pipeline",
            "value": round(weighted_val, 2),
            "source_board": "Deals",
            "source_board_id": "5030842959",
            "source_fields": ["deal_value", "closure_probability"],
            "records_total": total_deals,
            "records_used": len(weighted_eligible),
            "records_excluded": weighted_excluded_cnt,
            "exclusion_reason": "Missing deal value or closure probability",
            "calculation_coverage_pct": round((len(weighted_eligible) / total_deals * 100), 1) if total_deals > 0 else 0.0,
            "retrieved_at": now_ts
        }
    }

    # Data Quality Caveats
    caveats = []
    if len(deals_missing_val) > 0:
        caveats.append(f"{len(deals_missing_val)} of {total_deals} deals lack valid numeric deal values and were excluded from total pipeline valuation.")
    if weighted_excluded_cnt > 0:
        caveats.append(f"{weighted_excluded_cnt} of {total_deals} deals were excluded from weighted pipeline because value or probability was missing.")
    if deals_missing_close_date > 0:
        caveats.append(f"{deals_missing_close_date} deals lack expected close dates, affecting quarterly pacing projections.")

    return {
        "total_deals": total_deals,
        "open_deals_count": len(open_deals),
        "won_deals_count": len(won_deals),
        "lost_deals_count": len(lost_deals),
        "on_hold_completed_deals_count": len(hold_deals),
        "open_deals_value": round(sum(d["deal_value"] for d in open_deals if d.get("deal_value") is not None), 2),
        "total_pipeline_value": round(total_pipeline_val, 2),
        "deals_with_value_count": len(deals_with_val),
        "deals_missing_value_count": len(deals_missing_val),
        "average_deal_value": avg_deal_val,
        "median_deal_value": median_deal_val,
        "weighted_pipeline_value": round(weighted_val, 2),
        "weighted_deals_included_count": len(weighted_eligible),
        "weighted_deals_excluded_count": weighted_excluded_cnt,
        "win_rate_pct": win_rate_pct,
        "win_rate_details": win_rate_details,
        "pipeline_by_sector": pipeline_by_sector,
        "pipeline_by_stage": pipeline_by_stage,
        "pipeline_by_owner": pipeline_by_owner,
        "close_date_distribution": dict(sorted(close_date_monthly.items())),
        "deals_missing_close_date_count": deals_missing_close_date,
        "top_opportunities": top_opportunities,
        "concentration_risk": {
            "top_3_pct": top_3_pct,
            "top_5_pct": top_5_pct,
            "top_3_value": round(top_3_val, 2),
            "top_5_value": round(top_5_val, 2)
        },
        "stale_deals_count": len(stale_deals),
        "stale_deals": stale_deals,
        "calculation_coverage": {
            "total_records": total_deals,
            "used_records": len(deals_with_val),
            "excluded_records": len(deals_missing_val),
            "coverage_pct": round((len(deals_with_val) / total_deals * 100), 1) if total_deals > 0 else 0.0
        },
        "provenance": provenance,
        "data_quality_caveats": caveats
    }
