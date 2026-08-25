"""Standalone Monday.com read-only connection test script."""

import os
import sys
import asyncio

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from app.config import settings
from app.tools.monday_client import monday_client


async def main():
    print("=" * 60)
    print("Testing Live Monday.com API Connection (Strictly Read-Only)")
    print("=" * 60)
    print(f"Deals Board ID: {settings.MONDAY_DEALS_BOARD_ID}")
    print(f"Work Orders Board ID: {settings.MONDAY_WORK_ORDERS_BOARD_ID}")

    if not settings.MONDAY_API_TOKEN:
        print("[WARNING] MONDAY_API_TOKEN is not configured in .env.")
        return

    try:
        print("\n1. Running Health Check...")
        health = await monday_client.health_check()
        print(f"Health Status: {health.get('status')}")
        print(f"Deals Reachable: {health.get('boards', {}).get('deals', {}).get('reachable')} (Items: {health.get('boards', {}).get('deals', {}).get('item_count')})")
        print(f"Work Orders Reachable: {health.get('boards', {}).get('work_orders', {}).get('reachable')} (Items: {health.get('boards', {}).get('work_orders', {}).get('item_count')})")

        print("\n2. Testing Schema Introspection...")
        deals_schema = await monday_client.fetch_board_schema(settings.MONDAY_DEALS_BOARD_ID)
        print(f"Deals Board Name: {deals_schema.get('board_name')} with {len(deals_schema.get('columns', []))} columns.")

        print("\n3. Testing Mutation Blocking Guard...")
        try:
            await monday_client._execute_query("mutation { create_item(board_id: 123) { id } }")
            print("[CRITICAL ERROR] Mutation was not blocked!")
        except PermissionError:
            print("[OK] Mutation blocked successfully by read-only guard.")

        print("\n[SUCCESS] Monday.com connection verified successfully.")

    except Exception as e:
        print(f"[ERROR] Monday.com connection test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
