"""Celery configuration for scheduled background board polling (§3)."""

from celery import Celery
from app.config import settings

celery_app = Celery(
    "bi_agent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "refresh-monday-boards-every-5-min": {
            "task": "app.tasks.refresh_all_boards_task",
            "schedule": float(settings.CACHE_TTL_SECONDS),
        }
    }
)
