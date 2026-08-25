"""Unit tests for Multi-Tier Caching Layer (Redis + In-Memory Fallback)."""

import pytest
import asyncio
import time
from app.cache import (
    cache_set,
    cache_get,
    cache_delete,
    get_cached_board_items,
    set_cached_board_items,
    get_cached_metrics,
    set_cached_metrics,
    clear_board_cache,
    get_cache_status
)


@pytest.mark.asyncio
async def test_cache_set_and_get():
    """Verify basic set and get in cache layer."""
    await cache_set("test_key_1", {"message": "hello world"}, ttl_seconds=10)
    val = await cache_get("test_key_1")
    assert val is not None
    assert val.get("message") == "hello world"


@pytest.mark.asyncio
async def test_cache_ttl_expiry():
    """Verify item expires when TTL elapses."""
    await cache_set("test_key_expire", {"temp": 123}, ttl_seconds=1)
    val = await cache_get("test_key_expire")
    assert val == {"temp": 123}

    # Wait for TTL expiry
    await asyncio.sleep(1.1)
    expired_val = await cache_get("test_key_expire")
    assert expired_val is None


@pytest.mark.asyncio
async def test_cached_board_items():
    """Verify board items snapshot caching."""
    mock_items = [{"item_id": "1", "item_name": "Deal Alpha"}, {"item_id": "2", "item_name": "Deal Beta"}]
    await set_cached_board_items("board_999", mock_items, ttl=10)

    cached = await get_cached_board_items("board_999")
    assert cached is not None
    assert len(cached) == 2
    assert cached[0]["item_name"] == "Deal Alpha"


@pytest.mark.asyncio
async def test_cached_metrics_with_filter_hash():
    """Verify pre-computed metric caching with deterministic query filter hashing."""
    metrics_all = {"total_value": 1000000}
    metrics_filtered = {"total_value": 500000}

    await set_cached_metrics("pipeline", metrics_all, filters=None)
    await set_cached_metrics("pipeline", metrics_filtered, filters={"sector": "Energy"})

    res_all = await get_cached_metrics("pipeline")
    res_energy = await get_cached_metrics("pipeline", filters={"sector": "Energy"})
    res_mining = await get_cached_metrics("pipeline", filters={"sector": "Mining"})

    assert res_all == metrics_all
    assert res_energy == metrics_filtered
    assert res_mining is None


@pytest.mark.asyncio
async def test_cache_clear():
    """Verify cache flushing."""
    await cache_set("board:503:raw", [{"id": 1}], ttl_seconds=60)
    await clear_board_cache("503")
    assert await cache_get("board:503:raw") is None
