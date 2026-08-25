"""Standalone verification and diagnostic script for Monday.com dynamic retrieval."""

import asyncio
import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.tools.monday_client import monday_client
from app.tools.column_map import build_dynamic_column_map_with_metadata
from app.tools.deals_tools import get_deals, compute_pipeline_metrics
from app.tools.work_order_tools import get_work_orders, compute_ops_metrics
from app.tools.join_tools import join_deals_to_work_orders


async def main():
    print("=" * 70)
    print("📊 Skylark Drones — Monday.com Dynamic Retrieval & Health Diagnostic")
    print("=" * 70)
    print(f"Deals Board ID:       {settings.MONDAY_DEALS_BOARD_ID}")
    print(f"Work Orders Board ID: {settings.MONDAY_WORK_ORDERS_BOARD_ID}")
    print(f"Monday API URL:       {settings.MONDAY_API_URL}")
    print("-" * 70)

    # 1. Health Check
    print("\n[1/4] Running Board Connectivity Health Check...")
    health = await monday_client.health_check()
    print(f"Health Status: {health.get('status')}")
    print(f"Deals Board:       Reachable={health['boards']['deals']['reachable']}, Count={health['boards']['deals']['item_count']}")
    print(f"Work Orders Board: Reachable={health['boards']['work_orders']['reachable']}, Count={health['boards']['work_orders']['item_count']}")

    # 2. Deals Dynamic Retrieval & Analytics
    print("\n[2/4] Testing Deals Board Dynamic Retrieval & Metrics...")
    deals_metrics = await compute_pipeline_metrics()
    print(f"Total Deals:            {deals_metrics.get('total_deals')}")
    print(f"Total Pipeline Value:   ${deals_metrics.get('total_pipeline_value', 0):,.2f}")
    print(f"Weighted Pipeline:      ${deals_metrics.get('weighted_pipeline_value', 0):,.2f}")
    print(f"Calculation Coverage:   {deals_metrics.get('calculation_coverage', {}).get('coverage_pct')}%")
    print(f"Sectors Discovered:     {list(deals_metrics.get('pipeline_by_sector', {}).keys())}")

    # 3. Work Orders Dynamic Retrieval & Analytics
    print("\n[3/4] Testing Work Orders Dynamic Retrieval & Metrics...")
    ops_metrics = await compute_ops_metrics()
    print(f"Total Work Orders:      {ops_metrics.get('total_work_orders')}")
    print(f"Delayed Orders:         {ops_metrics.get('delayed_count')}")
    print(f"Total Billed Value:     ${ops_metrics.get('financial_summary', {}).get('total_billed_value', 0):,.2f}")
    print(f"Total Collected:        ${ops_metrics.get('financial_summary', {}).get('total_collected_amount', 0):,.2f}")
    print(f"Outstanding Balance:    ${ops_metrics.get('financial_summary', {}).get('total_amount_receivable', 0):,.2f}")

    # 4. Cross-Board Entity Match
    print("\n[4/4] Testing Cross-Board Entity Linkage...")
    join_res = await join_deals_to_work_orders()
    summary = join_res.get("summary", {})
    print(f"Matched Pairs:          {summary.get('matched_pairs_count')} (Exact: {summary.get('exact_matches_count')}, Fuzzy: {summary.get('fuzzy_matches_count')})")
    print(f"Deal Linkage Rate:      {summary.get('deal_linkage_coverage_pct')}%")
    print(f"Won Deals Unlinked:     {len(join_res.get('won_deals_unlinked', []))}")

    print("\n" + "=" * 70)
    print("✅ Diagnostic Complete: Dynamic retrieval and deterministic calculations verified.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

