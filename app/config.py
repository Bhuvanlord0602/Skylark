"""Configuration settings for Monday.com BI Agent with Groq + Qwen."""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Automatically load Streamlit Cloud secrets into environment variables
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if isinstance(v, str) and v.strip():
                os.environ[k] = v.strip()
except Exception:
    pass


class Settings(BaseSettings):
    # Groq / Qwen LLM Configuration
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "qwen/qwen3.6-27b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    # Monday.com API Configuration
    MONDAY_API_TOKEN: str = ""
    MONDAY_DEALS_BOARD_ID: str = "5030842959"
    MONDAY_WORK_ORDERS_BOARD_ID: str = "5030843495"
    MONDAY_API_URL: str = "https://api.monday.com/v2"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"

    # Fuzzy Join Threshold (token sort ratio 0-100)
    FUZZY_MATCH_THRESHOLD: float = 90.0

    # API Resilience Settings
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 1.5
    REQUEST_TIMEOUT: float = 30.0

    # Redis & Caching Configuration (§2)
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300
    SESSION_TTL_SECONDS: int = 86400
    USE_REDIS: bool = True

    # Background Polling / Refresh (§3)
    ENABLE_BACKGROUND_REFRESH: bool = True
    BACKGROUND_REFRESH_INTERVAL_SECONDS: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
