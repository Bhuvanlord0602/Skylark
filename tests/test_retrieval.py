"""Unit tests for Monday.com GraphQL API retrieval resilience and integrity."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.tools.monday_client import MondayClient


@pytest.mark.asyncio
async def test_strictly_read_only_blocks_mutations():
    """Verify that any mutation GraphQL query raises PermissionError immediately."""
    client = MondayClient(api_token="mock_token")
    mutation_query = "mutation { create_item (board_id: 123, item_name: 'Test') { id } }"
    with pytest.raises(PermissionError, match="strictly read-only"):
        await client._execute_query(mutation_query)


@pytest.mark.asyncio
async def test_cursor_pagination_fetches_all_pages():
    """Verify cursor pagination loop continues until next_items_page cursor is null."""
    client = MondayClient(api_token="mock_token")

    page1_response = {
        "data": {
            "boards": [{
                "id": "5030842959",
                "name": "deals",
                "items_page": {
                    "cursor": "cursor_page_2",
                    "items": [{"id": "1", "name": "Item 1", "column_values": []}]
                }
            }]
        }
    }
    page2_response = {
        "data": {
            "next_items_page": {
                "cursor": None,
                "items": [{"id": "2", "name": "Item 2", "column_values": []}]
            }
        }
    }

    with patch.object(client, "_execute_query", side_effect=[page1_response, page2_response]):
        items = await client.fetch_board_items("5030842959")
        assert len(items) == 2
        assert items[0]["item_id"] == "1"
        assert items[1]["item_id"] == "2"


@pytest.mark.asyncio
async def test_duplicate_item_id_detection():
    """Verify duplicate item IDs in API response are flagged in retrieval warnings."""
    client = MondayClient(api_token="mock_token")

    response_data = {
        "data": {
            "boards": [{
                "id": "5030842959",
                "name": "deals",
                "items_page": {
                    "cursor": None,
                    "items": [
                        {"id": "1001", "name": "Item 1", "column_values": []},
                        {"id": "1001", "name": "Item 1 Duplicate", "column_values": []}
                    ]
                }
            }]
        }
    }

    with patch.object(client, "_execute_query", return_value=response_data):
        items = await client.fetch_board_items("5030842959")
        assert len(items) == 2
        assert any("duplicate item IDs detected" in w for w in client.retrieval_warnings)


@pytest.mark.asyncio
async def test_health_check_handles_degraded_board():
    """Verify health check reports degraded status if one board fails."""
    client = MondayClient(api_token="mock_token")

    async def mock_fetch(board_id, limit=25):
        if str(board_id) == "5030842959":
            return [{"item_id": "1"}]
        raise RuntimeError("Work Orders board unreachable")

    with patch.object(client, "fetch_board_items", side_effect=mock_fetch):
        health = await client.health_check()
        assert health["status"] == "degraded"
        assert health["boards"]["deals"]["reachable"] is True
        assert health["boards"]["work_orders"]["reachable"] is False

