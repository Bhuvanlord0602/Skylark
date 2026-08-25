"""Unit tests for deterministic metric calculations (Deals, Work Orders, Cross-Board)."""

import pytest
from app.analytics.deals_metrics import compute_deals_analytics
from app.analytics.work_orders_metrics import compute_work_orders_analytics
from app.analytics.cross_board import compute_cross_board_analytics


def test_deals_analytics_calculation(mock_deals_raw_items):
    """Test mathematical precision and provenance of Deals pipeline metrics."""
    # Convert mock items to normalized format
    normalized_deals = [
        {
            "id": "1001",
            "deal_name": "Apex Solar Energy Ltd",
            "sector": "Energy",
            "stage": "Won",
            "deal_value": 150000.0,
            "closure_probability": 100.0,
            "owner": "Alice Walker"
        },
        {
            "id": "1002",
            "deal_name": "Zenith Healthcare Inc.",
            "sector": "Healthcare",
            "stage": "Proposal",
            "deal_value": 250000.0,
            "closure_probability": 60.0,
            "owner": "Bob Smith"
        },
        {
            "id": "1003",
            "deal_name": "Hyperion Cloud Tech LLC",
            "sector": "Technology",
            "stage": "Lost",
            "deal_value": 80000.0,
            "closure_probability": 0.0,
            "owner": "Alice Walker"
        },
        {
            "id": "1004",
            "deal_name": "Omni Global Logistics",
            "sector": "Logistics",
            "stage": "Negotiation",
            "deal_value": None,  # Missing value
            "closure_probability": None,
            "owner": "Charlie Davis"
        }
    ]

    res = compute_deals_analytics(normalized_deals, raw_deals_count=4)

    # 150k + 250k + 80k = 480k
    assert res["total_pipeline_value"] == 480000.0
    assert res["deals_with_value_count"] == 3
    assert res["deals_missing_value_count"] == 1

    # Weighted: (150k * 1.0) + (250k * 0.6) + (80k * 0.0) = 150k + 150k + 0 = 300,000
    assert res["weighted_pipeline_value"] == 300000.0
    assert res["weighted_deals_included_count"] == 3

    # Win rate: 1 Won / (1 Won + 1 Lost) = 50.0%
    assert res["win_rate_pct"] == 50.0

    # Provenance metadata
    prov = res["provenance"]
    assert "total_pipeline" in prov
    assert prov["total_pipeline"]["records_used"] == 3
    assert prov["total_pipeline"]["records_excluded"] == 1


def test_work_orders_analytics_calculation(mock_work_orders_raw_items):
    """Test Work Orders operational and financial metrics."""
    normalized_orders = [
        {
            "id": "2001",
            "deal_name": "Apex Solar Energy",
            "sector": "Energy",
            "execution_status": "Completed",
            "billed_value": 50000.0,
            "collected_amount": 48000.0,
            "amount_receivable": 2000.0,
            "start_date": "2025-01-01",
            "end_date": "2025-02-01"
        },
        {
            "id": "2002",
            "deal_name": "Zenith Healthcare",
            "sector": "Healthcare",
            "execution_status": "Delayed",
            "billed_value": 30000.0,
            "collected_amount": 10000.0,
            "amount_receivable": 20000.0,
            "start_date": "2025-01-15",
            "end_date": "2025-02-15"
        }
    ]

    res = compute_work_orders_analytics(normalized_orders, raw_wo_count=2)

    assert res["total_work_orders"] == 2
    assert res["completed_count"] == 1
    assert res["delayed_count"] == 1

    fin = res["financial_summary"]
    assert fin["total_billed_value"] == 80000.0
    assert fin["total_collected_amount"] == 58000.0
    assert fin["total_amount_receivable"] == 22000.0
    assert fin["collection_rate_pct"] == 72.5


def test_cross_board_analytics():
    """Test Sector Health Matrix generation and linkage calculations."""
    deals_metrics = {
        "pipeline_by_sector": {
            "Energy": {"total_value": 500000.0, "deal_count": 3, "win_rate_pct": 66.7, "avg_deal_size": 166666.7},
            "Healthcare": {"total_value": 250000.0, "deal_count": 2, "win_rate_pct": 50.0, "avg_deal_size": 125000.0}
        }
    }
    ops_metrics = {
        "work_orders_by_sector": {"Energy": 4, "Healthcare": 2},
        "delayed_by_sector": {"Energy": 1, "Healthcare": 1}
    }
    join_results = {
        "matched_records": [{"deal_id": "1", "work_order_id": "2001"}],
        "unmatched_deals": [],
        "unmatched_work_orders": [],
        "summary": {"matched_pairs_count": 1, "exact_matches_count": 1, "fuzzy_matches_count": 0}
    }

    res = compute_cross_board_analytics(deals_metrics, ops_metrics, join_results)
    matrix = res["sector_health_matrix"]

    assert len(matrix) == 2
    assert matrix[0]["sector"] == "Energy"
    assert matrix[0]["pipeline_value"] == 500000.0
    assert matrix[0]["work_order_count"] == 4
    assert matrix[0]["delayed_work_orders"] == 1

