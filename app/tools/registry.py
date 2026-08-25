"""Tool Registry and Safe Execution Dispatcher with explicit allowlist."""

import inspect
import asyncio
import logging
from typing import Any, Dict

from app.tools.deals_tools import (
    get_deals,
    compute_pipeline_metrics,
)
from app.tools.work_order_tools import (
    get_work_orders,
    compute_ops_metrics,
)
from app.tools.join_tools import (
    join_deals_to_work_orders,
)
from app.tools.leadership_tools import (
    generate_leadership_summary,
)
from app.tools.data_quality import (
    data_quality_report,
)

logger = logging.getLogger("tool_registry")

# Explicit Allowlist Registry - Arbitrary Python execution is strictly prevented
TOOL_REGISTRY = {
    "get_deals": get_deals,
    "get_work_orders": get_work_orders,
    "compute_pipeline_metrics": compute_pipeline_metrics,
    "compute_ops_metrics": compute_ops_metrics,
    "join_deals_to_work_orders": join_deals_to_work_orders,
    "data_quality_report": data_quality_report,
    "generate_leadership_summary": generate_leadership_summary,
}


async def execute_tool_async(name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute a registered tool asynchronously by name with validated arguments."""
    args = arguments or {}

    if name not in TOOL_REGISTRY:
        logger.warning(f"Rejected unknown tool request: {name}")
        return {
            "error": f"Unknown tool: {name}"
        }

    func = TOOL_REGISTRY[name]
    try:
        if inspect.iscoroutinefunction(func):
            return await func(**args)
        else:
            return func(**args)
    except Exception as exc:
        logger.error(f"Execution failed for tool '{name}': {exc}", exc_info=True)
        return {
            "error": "Tool execution failed",
            "details": str(exc),
        }


def execute_tool(name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    """Synchronous wrapper for tool execution."""
    args = arguments or {}

    if name not in TOOL_REGISTRY:
        return {
            "error": f"Unknown tool: {name}"
        }

    func = TOOL_REGISTRY[name]
    try:
        if inspect.iscoroutinefunction(func):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import nest_asyncio
                    nest_asyncio.apply()
                    return loop.run_until_complete(func(**args))
                return loop.run_until_complete(func(**args))
            except RuntimeError:
                return asyncio.run(func(**args))
        else:
            return func(**args)
    except Exception as exc:
        logger.error(f"Execution failed for tool '{name}': {exc}")
        return {
            "error": "Tool execution failed",
            "details": str(exc),
        }
