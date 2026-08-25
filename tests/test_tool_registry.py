"""Unit tests for Tool Registry and safe execution dispatcher."""

import pytest
from app.tools.registry import TOOL_REGISTRY, execute_tool_async, execute_tool


def test_tool_registry_contains_required_bi_tools():
    """Verify all 7 required BI tools are registered in allowlist."""
    expected_tools = [
        "get_deals",
        "get_work_orders",
        "compute_pipeline_metrics",
        "compute_ops_metrics",
        "join_deals_to_work_orders",
        "data_quality_report",
        "generate_leadership_summary"
    ]
    for tool_name in expected_tools:
        assert tool_name in TOOL_REGISTRY, f"Missing required tool: {tool_name}"


def test_execute_unknown_tool_fails_safely():
    """Verify attempting to call an unregistered tool returns an error safely."""
    res = execute_tool("execute_arbitrary_code", {"code": "import os; os.system('rm -rf')"})
    assert "error" in res
    assert "Unknown tool" in res["error"]


@pytest.mark.asyncio
async def test_execute_tool_async_unknown_tool():
    """Verify async execution of unknown tool is blocked."""
    res = await execute_tool_async("non_existent_tool", {})
    assert "error" in res
    assert "Unknown tool" in res["error"]
