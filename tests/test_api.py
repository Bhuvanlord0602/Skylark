"""Unit tests for FastAPI endpoints (/health, /schema, /chat, /leadership-summary, /data-quality, /provenance)."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test GET / returns API metadata and configured board IDs."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["llm_provider"] == "groq"
    assert "deals_board_id" in data["boards_configured"]


def test_schema_endpoint():
    """Test GET /schema returns active column maps and mapping metadata."""
    response = client.get("/schema")
    assert response.status_code == 200
    data = response.json()
    assert "deals_column_map" in data
    assert "work_orders_column_map" in data


def test_health_endpoint():
    """Test GET /health handles mocked health check."""
    mock_health = {
        "status": "healthy",
        "api_reachable": True,
        "boards": {
            "deals": {"reachable": True, "item_count": 42},
            "work_orders": {"reachable": True, "item_count": 18}
        },
        "errors": []
    }
    with patch("app.main.monday_client.health_check", new_callable=AsyncMock) as mock_hc:
        mock_hc.return_value = mock_health
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


def test_chat_endpoint(mock_deals_raw_items, mock_work_orders_raw_items):
    """Test POST /chat returns structured response, tool trace, and chart recommendations."""
    async def mock_fetch(board_id):
        from app.config import settings
        if str(board_id) == str(settings.MONDAY_DEALS_BOARD_ID):
            return mock_deals_raw_items
        return mock_work_orders_raw_items

    with patch("app.tools.monday_client.monday_client.fetch_board_items", side_effect=mock_fetch), \
         patch("app.tools.monday_client.monday_client.fetch_board_schema", side_effect=Exception("mock schema fallback")):
        payload = {
            "message": "How is our pipeline in the energy sector?",
            "conversation_history": []
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "tool_calls" in data
        assert "data_caveats" in data


def test_leadership_summary_endpoint(mock_deals_raw_items, mock_work_orders_raw_items):
    """Test POST /leadership-summary generates 8-section executive brief."""
    async def mock_fetch(board_id):
        from app.config import settings
        if str(board_id) == str(settings.MONDAY_DEALS_BOARD_ID):
            return mock_deals_raw_items
        return mock_work_orders_raw_items

    with patch("app.tools.monday_client.monday_client.fetch_board_items", side_effect=mock_fetch), \
         patch("app.tools.monday_client.monday_client.fetch_board_schema", side_effect=Exception("mock schema fallback")):
        payload = {
            "topic": "Executive Pipeline Review",
            "period": "Q3 2025"
        }
        response = client.post("/leadership-summary", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "markdown_summary" in data
        assert "headline" in data


def test_data_quality_endpoint(mock_deals_raw_items, mock_work_orders_raw_items):
    """Test GET /data-quality returns board scores and cross-board join stats."""
    async def mock_fetch(board_id):
        from app.config import settings
        if str(board_id) == str(settings.MONDAY_DEALS_BOARD_ID):
            return mock_deals_raw_items
        return mock_work_orders_raw_items

    with patch("app.tools.monday_client.monday_client.fetch_board_items", side_effect=mock_fetch), \
         patch("app.tools.monday_client.monday_client.fetch_board_schema", side_effect=Exception("mock schema fallback")):
        response = client.get("/data-quality")
        assert response.status_code == 200
        data = response.json()
        assert "deals_board" in data
        assert "work_orders_board" in data
        assert "cross_board_join" in data


def test_metric_provenance_endpoint(mock_deals_raw_items, mock_work_orders_raw_items):
    """Test GET /provenance/{metric_name} returns calculation lineage."""
    async def mock_fetch(board_id):
        from app.config import settings
        if str(board_id) == str(settings.MONDAY_DEALS_BOARD_ID):
            return mock_deals_raw_items
        return mock_work_orders_raw_items

    with patch("app.tools.monday_client.monday_client.fetch_board_items", side_effect=mock_fetch), \
         patch("app.tools.monday_client.monday_client.fetch_board_schema", side_effect=Exception("mock schema fallback")):
        response = client.get("/provenance/total_pipeline")
        assert response.status_code == 200
        data = response.json()
        assert data["metric"] == "total_pipeline"
        assert "source_board" in data
        assert "calculation_coverage_pct" in data


def test_refresh_endpoint():
    """Test POST /refresh schedules background board extraction and returns immediately."""
    with patch("app.main.execute_board_refresh_workflow", new_callable=AsyncMock) as mock_task:
        response = client.post("/refresh")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "refresh_initiated"
        assert "requested_at" in data


def test_chat_with_session_id(mock_deals_raw_items, mock_work_orders_raw_items):
    """Test POST /chat with persistent session_id retains conversation memory."""
    async def mock_fetch(board_id):
        from app.config import settings
        if str(board_id) == str(settings.MONDAY_DEALS_BOARD_ID):
            return mock_deals_raw_items
        return mock_work_orders_raw_items

    with patch("app.tools.monday_client.monday_client.fetch_board_items", side_effect=mock_fetch), \
         patch("app.tools.monday_client.monday_client.fetch_board_schema", side_effect=Exception("mock schema fallback")):
        payload = {
            "message": "What is our total pipeline?",
            "session_id": "test_session_api"
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("session_id") == "test_session_api"

