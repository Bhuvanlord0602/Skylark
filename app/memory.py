"""Conversation Memory & Multi-Turn Session State (§2.2).

Stores conversation turns in Redis with automatic In-Memory fallback.
Enables contextual multi-turn queries (e.g. "what about last quarter instead?")
without requiring re-statement of earlier prompts.
"""

from __future__ import annotations

import json
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings
from app.cache import get_redis_client

logger = logging.getLogger("app.memory")

# In-Memory session fallback: {session_id: {"history": [...], "expires_at": float}}
_IN_MEMORY_SESSIONS: Dict[str, Dict[str, Any]] = {}


async def get_session_history(session_id: str) -> List[Dict[str, Any]]:
    """Retrieve full conversation history list for the specified session ID."""
    if not session_id or not session_id.strip():
        return []

    # 1. Try Redis
    redis = await get_redis_client()
    if redis:
        try:
            raw = await redis.get(f"session:{session_id}:history")
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.warning(f"Redis get_session_history failed for {session_id}: {e}")

    # 2. In-Memory fallback
    entry = _IN_MEMORY_SESSIONS.get(session_id)
    if entry:
        if time.time() < entry["expires_at"]:
            return entry["history"]
        else:
            del _IN_MEMORY_SESSIONS[session_id]

    return []


async def append_session_turn(
    session_id: str,
    role: str,
    content: str,
    max_turns: int = 20,
    ttl_seconds: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Append a message turn (user or assistant) to session history, capping at max_turns."""
    if not session_id or not session_id.strip():
        return []

    ttl = ttl_seconds or settings.SESSION_TTL_SECONDS
    history = await get_session_history(session_id)

    new_turn = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    history.append(new_turn)

    # Cap to max turns (e.g. last 20 turns)
    if len(history) > max_turns:
        history = history[-max_turns:]

    now = time.time()
    serialized = json.dumps(history, default=str)

    # 1. Store in memory
    _IN_MEMORY_SESSIONS[session_id] = {
        "history": history,
        "expires_at": now + ttl,
        "updated_at": now
    }

    # 2. Store in Redis
    redis = await get_redis_client()
    if redis:
        try:
            await redis.set(f"session:{session_id}:history", serialized, ex=ttl)
        except Exception as e:
            logger.warning(f"Redis append_session_turn failed for {session_id}: {e}")

    return history


async def clear_session_history(session_id: str) -> None:
    """Clear conversation history for a specific session."""
    _IN_MEMORY_SESSIONS.pop(session_id, None)
    redis = await get_redis_client()
    if redis:
        try:
            await redis.delete(f"session:{session_id}:history")
        except Exception as e:
            logger.warning(f"Redis clear_session_history failed for {session_id}: {e}")


def get_memory_stats() -> Dict[str, Any]:
    """Return active conversation memory counts."""
    return {
        "in_memory_active_sessions": len(_IN_MEMORY_SESSIONS),
        "session_ttl_seconds": settings.SESSION_TTL_SECONDS
    }
