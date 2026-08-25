"""Unit tests for GroqLLMClient."""

import os
import pytest
from unittest.mock import MagicMock, patch
from app.llm_client import GroqLLMClient


def test_groq_client_init_requires_api_key():
    """Verify GroqLLMClient raises ValueError if GROQ_API_KEY is missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="GROQ_API_KEY is missing"):
            GroqLLMClient(api_key="")


def test_groq_client_init_success():
    """Verify GroqLLMClient initializes OpenAI client with Groq base URL and configured model."""
    client = GroqLLMClient(api_key="gsk_test_mock_key_123", model="qwen/qwen3-32b")
    assert client.model == "qwen/qwen3-32b"
    assert client.client.base_url == "https://api.groq.com/openai/v1/"
    assert client.client.api_key == "gsk_test_mock_key_123"


def test_groq_client_chat_delegation():
    """Verify chat() delegates properly to OpenAI chat.completions.create with tools."""
    client = GroqLLMClient(api_key="gsk_test_mock_key_123", model="qwen/qwen3-32b")
    mock_resp = MagicMock()
    
    with patch.object(client.client.chat.completions, "create", return_value=mock_resp) as mock_create:
        messages = [{"role": "user", "content": "Hello"}]
        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        
        result = client.chat(messages=messages, tools=tools)
        assert result == mock_resp
        mock_create.assert_called_once_with(
            model="qwen/qwen3-32b",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
