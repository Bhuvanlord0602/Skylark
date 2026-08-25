"""Groq LLM Client using OpenAI-compatible SDK for Qwen model."""

import os
from openai import OpenAI


class GroqLLMClient:
    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        key = api_key or os.getenv("GROQ_API_KEY")

        if not key:
            raise ValueError(
                "GROQ_API_KEY is missing. Add it to your .env file."
            )

        self.model = model or os.getenv("GROQ_MODEL", "qwen/qwen3-32b")

        if not self.model:
            raise ValueError(
                "GROQ_MODEL is missing."
            )

        self.base_url = base_url or os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=key,
        )

    def chat(self, messages, tools=None):
        """Execute chat completion call to Groq with optional tool definitions."""
        kwargs = {
            "model": self.model,
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return self.client.chat.completions.create(**kwargs)
