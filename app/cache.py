"""Multi-Tier Caching Layer (Redis with automatic In-Memory Fallback).

Supports:
1. Board snapshots: `board:{board_id}:raw`
2. Computed metrics: `metrics:{metric_name}:{filters_hash}`
3. Stale-if-available serving & background refresh triggers.
"""

from __future__ import annotations

import json
import time
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger("app.cache")

# Global in-memory cache fallback: {key: {"value": data, "expires_at": float, "cached_at": float}}
_IN_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}
_REDIS_CLIENT = None
_REDIS_AVAILABLE: Optional[bool] = None


async def get_redis_client():
    """Obtain or initialize async Redis client if configured and available."""
    global _REDIS_CLIENT, _REDIS_AVAILABLE
    if not settings.USE_REDIS:
        _REDIS_AVAILABLE = False
        return None

    if _REDIS_CLIENT is None and _REDIS_AVAILABLE is not False:
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(
                settings.REDIS_URL,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                decode_responses=True
            )
            # Test ping
            await client.ping()
            _REDIS_CLIENT = client
            _REDIS_AVAILABLE = True
            logger.info(f"Connected to Redis cache at {settings.REDIS_URL}")
        except Exception:
            logger.info("Using built-in in-memory caching layer (TTL=300s).")
            _REDIS_AVAILABLE = False
            _REDIS_CLIENT = None

    return _REDIS_CLIENT


def _make_filter_hash(filters: Optional[Dict[str, Any]]) -> str:
    """Generate deterministic MD5 hash for arbitrary query filter dictionaries."""
    if not filters:
        return "all"
    serialized = json.dumps(filters, sort_keys=True, default=str)
    return hashlib.md5(serialized.encode("utf-8")).hexdigest()[:10]


# --- Low-Level Cache Primitives ---

async def cache_get(key: str) -> Optional[Any]:
    """Retrieve item from Redis or In-Memory fallback."""
    # 1. Try Redis
    redis = await get_redis_client()
    if redis:
        try:
            val = await redis.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Redis GET failed for key {key}: {e}. Checking in-memory.")

    # 2. In-Memory fallback
    entry = _IN_MEMORY_CACHE.get(key)
    if entry:
        if time.time() < entry["expires_at"]:
            return entry["value"]
        else:
            # Expired
            del _IN_MEMORY_CACHE[key]

    return None


async def cache_set(key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
    """Store item in Redis and In-Memory fallback with TTL."""
    ttl = ttl_seconds or settings.CACHE_TTL_SECONDS
    serialized = json.dumps(value, default=str)
    now = time.time()

    # 1. Store in memory
    _IN_MEMORY_CACHE[key] = {
        "value": value,
        "cached_at": now,
        "expires_at": now + ttl
    }

    # 2. Store in Redis
    redis = await get_redis_client()
    if redis:
        try:
            await redis.set(key, serialized, ex=ttl)
        except Exception as e:
            logger.warning(f"Redis SET failed for key {key}: {e}")


async def cache_delete(key: str) -> None:
    """Delete key from both Redis and in-memory cache."""
    _IN_MEMORY_CACHE.pop(key, None)
    redis = await get_redis_client()
    if redis:
        try:
            await redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis DEL failed for key {key}: {e}")


# --- Domain Caching API (§2.1) ---

async def get_cached_board_items(board_id: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve raw/normalized board items snapshot from cache."""
    key = f"board:{board_id}:raw"
    return await cache_get(key)


async def set_cached_board_items(board_id: str, items: List[Dict[str, Any]], ttl: Optional[int] = None) -> None:
    """Save raw board items snapshot to cache."""
    key = f"board:{board_id}:raw"
    await cache_set(key, items, ttl_seconds=ttl)


async def get_cached_metrics(metric_name: str, filters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Retrieve pre-computed analytics metric dictionary."""
    f_hash = _make_filter_hash(filters)
    key = f"metrics:{metric_name}:{f_hash}"
    return await cache_get(key)


async def set_cached_metrics(
    metric_name: str,
    data: Dict[str, Any],
    filters: Optional[Dict[str, Any]] = None,
    ttl: Optional[int] = None
) -> None:
    """Save pre-computed analytics metric dictionary to cache."""
    f_hash = _make_filter_hash(filters)
    key = f"metrics:{metric_name}:{f_hash}"
    await cache_set(key, data, ttl_seconds=ttl)


async def clear_board_cache(board_id: Optional[str] = None) -> None:
    """Clear cached data for a specific board or all boards."""
    global _IN_MEMORY_CACHE
    if board_id:
        await cache_delete(f"board:{board_id}:raw")
    else:
        _IN_MEMORY_CACHE.clear()
        redis = await get_redis_client()
        if redis:
            try:
                keys = await redis.keys("board:*") + await redis.keys("metrics:*")
                if keys:
                    await redis.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis flush failed: {e}")


def get_cache_status() -> Dict[str, Any]:
    """Return status of Redis connection and in-memory key counts."""
    return {
        "redis_connected": bool(_REDIS_AVAILABLE),
        "in_memory_keys_count": len(_IN_MEMORY_CACHE),
        "cache_ttl_seconds": settings.CACHE_TTL_SECONDS
    }
