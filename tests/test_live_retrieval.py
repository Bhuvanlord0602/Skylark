"""Opt-in live Monday.com integration tests.

To run these tests against the live Monday.com boards:
PowerShell:
    $env:RUN_LIVE_TESTS="1"
    python -m pytest tests/test_live_retrieval.py -v -s
"""

import os
import pytest
from app.config import settings
from app.tools.monday_client import monday_client
from app.tools.deals_tools import get_deals, compute_pipeline_metrics
from app.tools.work_order_tools import get_work_orders, compute_ops_metrics
from app.tools.join_tools import join_deals_to_work_orders

RUN_LIVE = os.getenv("RUN_LIVE_TESTS") == "1"


@pytest.mark.skipif(not RUN_LIVE, reason="Live tests require $env:RUN_LIVE_TESTS='1' with valid MONDAY_API_TOKEN")
@pytest.mark.asyncio
async def test_live_monday_health_check():
    """Verify live connectivity and accessibility of both configured boards."""
    health = await monday_client.health_check()
    assert health["api_reachable"] is True
    assert health["boards"]["deals"]["reachable"] is True
    assert health["boards"]["work_orders"]["reachable"] is True
    print(f"\n[LIVE TEST] Health: {health}")


@pytest.mark.skipif(not RUN_LIVE, reason="Live tests require $env:RUN_LIVE_TESTS='1' with valid MONDAY_API_TOKEN")
@pytest.mark.asyncio
async def test_live_deals_board_retrieval_and_metrics():
    """Verify dynamic retrieval and pipeline calculation from live Deals board."""
    deals_data = await get_deals()
    assert deals_data["total_retrieved"] > 0
    assert len(deals_data["deals"]) > 0

    metrics = await compute_pipeline_metrics()
    assert metrics["total_deals"] > 0
    assert "total_pipeline_value" in metrics
    print(f"\n[LIVE TEST] Deals Retrieved: {len(deals_data['deals'])}, Pipeline Value: ${metrics['total_pipeline_value']:,.2f}")


@pytest.mark.skipif(not RUN_LIVE, reason="Live tests require $env:RUN_LIVE_TESTS='1' with valid MONDAY_API_TOKEN")
@pytest.mark.asyncio
async def test_live_work_orders_board_retrieval_and_metrics():
    """Verify dynamic retrieval and operational metrics from live Work Orders board."""
    wo_data = await get_work_orders()
    assert wo_data["total_retrieved"] > 0
    assert len(wo_data["work_orders"]) > 0

    metrics = await compute_ops_metrics()
    assert metrics["total_work_orders"] > 0
    print(f"\n[LIVE TEST] Work Orders Retrieved: {len(wo_data['work_orders'])}, Delayed Count: {metrics['delayed_count']}")


@pytest.mark.skipif(not RUN_LIVE, reason="Live tests require $env:RUN_LIVE_TESTS='1' with valid MONDAY_API_TOKEN")
@pytest.mark.asyncio
async def test_live_cross_board_join():
    """Verify cross-board entity matching on live boards."""
    join_data = await join_deals_to_work_orders()
    summary = join_data["summary"]
    assert summary["total_deals"] > 0
    assert summary["total_work_orders"] > 0
    print(f"\n[LIVE TEST] Cross-Board Linkage: {summary['matched_pairs_count']} pairs ({summary['deal_linkage_coverage_pct']}%)")

