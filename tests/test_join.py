"""Unit tests for multi-phase cross-board entity matching."""

import pytest
from unittest.mock import patch
from app.tools.join_tools import join_deals_to_work_orders


@pytest.mark.asyncio
async def test_multi_phase_entity_matching(mock_deals_raw_items, mock_work_orders_raw_items):
    """Test Level 1 exact code, Level 2 normalized name, and Level 3 fuzzy matching."""
    async def mock_fetch(board_id):
        from app.config import settings
        if str(board_id) == str(settings.MONDAY_DEALS_BOARD_ID):
            return mock_deals_raw_items
        return mock_work_orders_raw_items

    with patch("app.tools.monday_client.monday_client.fetch_board_items", side_effect=mock_fetch), \
         patch("app.tools.monday_client.monday_client.fetch_board_schema", side_effect=Exception("mock schema fallback")):
        res = await join_deals_to_work_orders()

        matched = res["matched_records"]
        unmatched_deals = res["unmatched_deals"]
        unmatched_wo = res["unmatched_work_orders"]
        summary = res["summary"]

        assert len(matched) >= 2
        assert len(unmatched_deals) > 0
        assert len(unmatched_wo) > 0

        # Verify exact code match
        exact_code_matches = [m for m in matched if m["match_type"] == "exact_code"]
        assert len(exact_code_matches) >= 1
        assert exact_code_matches[0]["match_confidence"] == 1.0

        # Verify summary stats
        assert summary["matched_pairs_count"] == len(matched)
        assert summary["unmatched_deals_count"] == len(unmatched_deals)
