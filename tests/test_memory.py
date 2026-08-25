"""Unit tests for Conversation Memory & Multi-Turn Session State."""

import pytest
import asyncio
from app.memory import (
    get_session_history,
    append_session_turn,
    clear_session_history,
    get_memory_stats
)


@pytest.mark.asyncio
async def test_session_history_append_and_retrieve():
    """Verify appending conversation turns preserves role, content, and timestamp."""
    session_id = "test_sess_001"
    await clear_session_history(session_id)

    await append_session_turn(session_id, "user", "What is the Energy pipeline?")
    await append_session_turn(session_id, "assistant", "Energy pipeline is $45M.")

    history = await get_session_history(session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "What is the Energy pipeline?"
    assert history[1]["role"] == "assistant"
    assert "timestamp" in history[0]


@pytest.mark.asyncio
async def test_session_history_capping_max_turns():
    """Verify conversation history is capped at max_turns (e.g. 20 turns)."""
    session_id = "test_sess_cap"
    await clear_session_history(session_id)

    # Append 25 turns with max_turns=10
    for i in range(25):
        await append_session_turn(session_id, "user", f"Query {i}", max_turns=10)

    history = await get_session_history(session_id)
    assert len(history) == 10
    assert history[-1]["content"] == "Query 24"
    assert history[0]["content"] == "Query 15"


@pytest.mark.asyncio
async def test_multi_session_isolation():
    """Verify different sessions maintain isolated conversation contexts."""
    sess_a = "session_alice"
    sess_b = "session_bob"

    await clear_session_history(sess_a)
    await clear_session_history(sess_b)

    await append_session_turn(sess_a, "user", "Alice's query")
    await append_session_turn(sess_b, "user", "Bob's query")

    hist_a = await get_session_history(sess_a)
    hist_b = await get_session_history(sess_b)

    assert len(hist_a) == 1 and hist_a[0]["content"] == "Alice's query"
    assert len(hist_b) == 1 and hist_b[0]["content"] == "Bob's query"
