"""Deterministic Operational and Financial Metric Engine for Work Orders board.

Calculates execution health, delivery velocity, billing, collection, and receivables strictly
from validated Monday.com work order items.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict


def compute_work_orders_analytics(
    work_orders: List[Dict[str, Any]],
    raw_wo_count: int,
    data_quality_report: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Compute complete deterministic operational and financial analytics from normalized work orders."""
    total_wo = len(work_orders)
    
    if total_wo == 0:
        return {
            "total_work_orders": 0,
            "status_breakdown": {},
            "delayed_work_orders_count": 0,
            "delayed_work_orders": [],
            "delayed_by_sector": {},
            "delayed_by_region": {},
            "on_time_delivery_pct": None,
            "financial_summary": {
                "total_billed_value": 0.0,
                "total_collected_amount": 0.0,
                "total_amount_receivable": 0.0,
                "collection_rate_pct": 0.0
            },
            "timeline_coverage": {"valid_date_ranges": 0, "total_records": 0, "coverage_pct": 0.0},
            "calculation_coverage": {
                "total_records": raw_wo_count,
                "used_records": 0,
                "excluded_records": raw_wo_count,
                "coverage_pct": 0.0
            },
            "provenance": {},
            "data_quality_caveats": ["No work order records found."]
        }

    # 1. Execution Status Breakdown
    status_counts: Dict[str, int] = defaultdict(int)
    for wo in work_orders:
        st = wo.get("execution_status") or wo.get("status") or "Unspecified"
        status_counts[st] += 1

    status_breakdown: Dict[str, Dict[str, Any]] = {}
    for st, count in status_counts.items():
        status_breakdown[st] = {
            "count": count,
            "pct": round((count / total_wo * 100), 1)
        }

    # 2. Delayed / At-Risk Work Orders
    delayed_orders = []
    for wo in work_orders:
        st = str(wo.get("execution_status") or wo.get("status") or "").lower()
        if "delay" in st or "risk" in st or "blocked" in st:
            delayed_orders.append(wo)

    delayed_by_sector: Dict[str, int] = defaultdict(int)
    delayed_by_region: Dict[str, int] = defaultdict(int)
    for wo in delayed_orders:
        sec = wo.get("sector") or "Unspecified"
        reg = wo.get("region") or "Unassigned"
        delayed_by_sector[sec] += 1
        delayed_by_region[reg] += 1

    # 3. Work Orders by Sector
    sector_counts: Dict[str, int] = defaultdict(int)
    for wo in work_orders:
        sec = wo.get("sector") or "Unspecified"
        sector_counts[sec] += 1

    # 4. On-Time Delivery Rate
    completed_orders = [
        wo for wo in work_orders
        if "completed" in str(wo.get("execution_status") or wo.get("status") or "").lower()
    ]
    if len(completed_orders) > 0:
        on_time_orders = [
            wo for wo in completed_orders
            if not ("delay" in str(wo.get("execution_status") or "").lower())
        ]
        on_time_pct = round((len(on_time_orders) / len(completed_orders) * 100), 1)
    else:
        on_time_pct = None

    # 5. Financial Metrics (Billed Value, Collected Amount, Amount Receivable)
    billed_records = [wo for wo in work_orders if wo.get("billed_value") is not None]
    collected_records = [wo for wo in work_orders if wo.get("collected_amount") is not None]
    receivable_records = [wo for wo in work_orders if wo.get("amount_receivable") is not None]

    total_billed = sum(wo["billed_value"] for wo in billed_records)
    total_collected = sum(wo["collected_amount"] for wo in collected_records)
    total_receivable = sum(wo["amount_receivable"] for wo in receivable_records)

    collection_rate = round((total_collected / total_billed * 100), 1) if total_billed > 0 else 0.0

    # Invoice and Billing Status Breakdowns
    invoice_status_counts: Dict[str, int] = defaultdict(int)
    billing_status_counts: Dict[str, int] = defaultdict(int)
    collection_status_counts: Dict[str, int] = defaultdict(int)

    for wo in work_orders:
        if wo.get("invoice_status"):
            invoice_status_counts[str(wo["invoice_status"])] += 1
        if wo.get("billing_status"):
            billing_status_counts[str(wo["billing_status"])] += 1
        if wo.get("collection_status"):
            collection_status_counts[str(wo["collection_status"])] += 1

    # 6. Timeline Date Coverage Check
    valid_timeline_records = []
    for wo in work_orders:
        s_date = wo.get("start_date") or wo.get("probable_start_date")
        e_date = wo.get("end_date") or wo.get("probable_end_date")
        if s_date and e_date and len(s_date) >= 10 and len(e_date) >= 10:
            valid_timeline_records.append({
                "deal_name": wo.get("deal_name") or wo.get("client") or f"WO #{wo.get('id')}",
                "sector": wo.get("sector") or "Unspecified",
                "start_date": s_date[:10],
                "end_date": e_date[:10],
                "execution_status": wo.get("execution_status") or wo.get("status") or "Active",
                "region": wo.get("region")
            })

    timeline_coverage_pct = round((len(valid_timeline_records) / total_wo * 100), 1) if total_wo > 0 else 0.0

    # 7. Provenance Metadata
    now_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    provenance = {
        "billed_value": {
            "metric": "total_billed_value",
            "value": round(total_billed, 2),
            "source_board": "Work Orders",
            "source_board_id": "5030843495",
            "source_fields": ["billed_value"],
            "records_total": total_wo,
            "records_used": len(billed_records),
            "records_excluded": total_wo - len(billed_records),
            "exclusion_reason": "Missing or unparseable billed value",
            "calculation_coverage_pct": round((len(billed_records) / total_wo * 100), 1) if total_wo > 0 else 0.0,
            "retrieved_at": now_ts
        },
        "collected_amount": {
            "metric": "total_collected_amount",
            "value": round(total_collected, 2),
            "source_board": "Work Orders",
            "source_board_id": "5030843495",
            "source_fields": ["collected_amount"],
            "records_total": total_wo,
            "records_used": len(collected_records),
            "records_excluded": total_wo - len(collected_records),
            "exclusion_reason": "Missing or unparseable collected amount",
            "calculation_coverage_pct": round((len(collected_records) / total_wo * 100), 1) if total_wo > 0 else 0.0,
            "retrieved_at": now_ts
        },
        "amount_receivable": {
            "metric": "total_amount_receivable",
            "value": round(total_receivable, 2),
            "source_board": "Work Orders",
            "source_board_id": "5030843495",
            "source_fields": ["amount_receivable"],
            "records_total": total_wo,
            "records_used": len(receivable_records),
            "records_excluded": total_wo - len(receivable_records),
            "exclusion_reason": "Missing or unparseable receivable amount",
            "calculation_coverage_pct": round((len(receivable_records) / total_wo * 100), 1) if total_wo > 0 else 0.0,
            "retrieved_at": now_ts
        }
    }

    # Data Quality Caveats
    caveats = []
    if len(delayed_orders) > 0:
        caveats.append(f"{len(delayed_orders)} of {total_wo} work orders are flagged as delayed or at-risk.")
    if len(billed_records) < total_wo:
        caveats.append(f"Financial billed metrics are calculated from {len(billed_records)} of {total_wo} work orders with populated billed values.")
    if timeline_coverage_pct < 50.0:
        caveats.append(f"Timeline Gantt availability is limited because only {len(valid_timeline_records)} of {total_wo} ({timeline_coverage_pct}%) work orders have complete start and end date ranges.")

    return {
        "total_work_orders": total_wo,
        "status_breakdown": status_breakdown,
        "completed_count": len(completed_orders),
        "delayed_count": len(delayed_orders),
        "delayed_by_sector": dict(delayed_by_sector),
        "delayed_by_region": dict(delayed_by_region),
        "work_orders_by_sector": dict(sector_counts),
        "on_time_delivery_pct": on_time_pct,
        "financial_summary": {
            "total_billed_value": round(total_billed, 2),
            "total_collected_amount": round(total_collected, 2),
            "total_amount_receivable": round(total_receivable, 2),
            "collection_rate_pct": collection_rate,
            "billed_records_count": len(billed_records),
            "collected_records_count": len(collected_records),
            "receivable_records_count": len(receivable_records)
        },
        "invoice_status_breakdown": dict(invoice_status_counts),
        "billing_status_breakdown": dict(billing_status_counts),
        "collection_status_breakdown": dict(collection_status_counts),
        "timeline_data": valid_timeline_records,
        "timeline_coverage": {
            "valid_date_ranges_count": len(valid_timeline_records),
            "total_records": total_wo,
            "coverage_pct": timeline_coverage_pct
        },
        "calculation_coverage": {
            "total_records": total_wo,
            "used_records": len(billed_records) if billed_records else total_wo,
            "coverage_pct": round((len(billed_records) / total_wo * 100), 1) if total_wo > 0 and billed_records else 100.0
        },
        "provenance": provenance,
        "data_quality_caveats": caveats
    }

