"""Provenance and Metric Explainability Tool ('Why this number?').

Provides complete mathematical and data lineage traceability for every computed metric.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from app.tools.deals_tools import compute_pipeline_metrics
from app.tools.work_order_tools import compute_ops_metrics


async def get_metric_provenance(metric_name: str) -> Dict[str, Any]:
    """Retrieve full calculation lineage and data quality metadata for a given metric."""
    clean_name = metric_name.strip().lower()

    # Pipeline Metrics
    if any(k in clean_name for k in ("pipeline", "deal", "win_rate")):
        deals_metrics = await compute_pipeline_metrics()
        prov_map = deals_metrics.get("provenance", {})
        
        if "weighted" in clean_name and "weighted_pipeline" in prov_map:
            return prov_map["weighted_pipeline"]
        if "total_pipeline" in prov_map:
            return prov_map["total_pipeline"]

    # Operational / Financial Metrics
    if any(k in clean_name for k in ("billed", "collected", "receivable", "delay", "order")):
        ops_metrics = await compute_ops_metrics()
        prov_map = ops_metrics.get("provenance", {})

        if "billed" in clean_name and "billed_value" in prov_map:
            return prov_map["billed_value"]
        if "collected" in clean_name and "collected_amount" in prov_map:
            return prov_map["collected_amount"]
        if "receivable" in clean_name and "amount_receivable" in prov_map:
            return prov_map["amount_receivable"]

    return {
        "metric": metric_name,
        "status": "not_found",
        "message": f"No specific provenance record found for '{metric_name}'."
    }

