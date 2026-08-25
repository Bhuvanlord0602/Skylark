"""Unit tests for Groq Qwen Agent, tool schemas, and fallback analyzer."""

import pytest
from unittest.mock import patch, AsyncMock
from app.agent import BusinessIntelligenceAgent, run_agent, load_system_prompt
from app.tools.schemas import TOOLS
from app.tools.registry import execute_tool_async


def test_groq_tools_schema_integrity():
    """Verify tool schemas conform to OpenAI/Groq function calling format."""
    tool_names = [t["function"]["name"] for t in TOOLS]
    assert "compute_pipeline_metrics" in tool_names
    assert "get_deals" in tool_names
    assert "compute_ops_metrics" in tool_names
    assert "get_work_orders" in tool_names
    assert "join_deals_to_work_orders" in tool_names
    assert "data_quality_report" in tool_names
    assert "generate_leadership_summary" in tool_names

    for tool in TOOLS:
        assert tool["type"] == "function"
        fn = tool["function"]
        assert "description" in fn
        assert "parameters" in fn
        assert fn["parameters"]["type"] == "object"


def test_system_prompt_loading():
    """Verify system prompt is loaded and contains mandatory executive BI rules."""
    prompt = load_system_prompt()
    assert len(prompt) > 100
    assert "Monday.com is the source of truth" in prompt
    assert "Never invent numbers" in prompt
    assert "strictly read-only" in prompt


@pytest.mark.asyncio
async def test_dispatch_tool_get_deals(mock_deals_raw_items):
    """Test tool execution dynamically runs get_deals."""
    with patch("app.tools.monday_client.monday_client.fetch_board_items", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_deals_raw_items
        res = await execute_tool_async("get_deals", {"filters": {"sector": "energy"}})
        assert "deals" in res
        assert res["board_name"] == "deals"


@pytest.mark.asyncio
async def test_agent_deterministic_fallback(mock_deals_raw_items, mock_work_orders_raw_items):
    """Test deterministic fallback analyzer generates structured executive answers."""
    async def mock_fetch(board_id):
        from app.config import settings
        if str(board_id) == str(settings.MONDAY_DEALS_BOARD_ID):
            return mock_deals_raw_items
        return mock_work_orders_raw_items

    with patch("app.tools.monday_client.monday_client.fetch_board_items", side_effect=mock_fetch), \
         patch("app.tools.monday_client.monday_client.fetch_board_schema", side_effect=Exception("mock schema fallback")):
        res = await run_agent("How is our pipeline looking in the Energy sector?")
        assert "response" in res
        assert "tool_calls" in res
        assert "recommended_chart" in res
        assert res["recommended_chart"] == "pipeline_by_sector"
        text = res["response"]
        assert "Direct Answer" in text
        assert "Key Numbers" in text
        assert "Strategic Insight" in text
        assert "Data Quality & Confidence Caveats" in text
