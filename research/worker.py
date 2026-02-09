"""Celery worker configuration for research tasks.

Provides Redis-based task queue management with async execution support.
"""

import logging
import os
from typing import Any

from celery import Celery
from celery.result import AsyncResult

# Configure logging
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_BACKEND_URL = os.getenv("REDIS_BACKEND_URL", REDIS_URL)

# Celery configuration
celery_app = Celery(
    "research",
    broker=REDIS_URL,
    backend=REDIS_BACKEND_URL,
    include=["research.tasks"],
)

# Task queue configuration
celery_app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone settings
    timezone="UTC",
    enable_utc=True,
    # Task execution settings
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # Soft limit at 4 minutes
    # Result backend settings
    result_backend=REDIS_BACKEND_URL,
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    # Queue configuration
    task_default_queue="research",
    task_routes={
        "research.tasks.web_search": {"queue": "research"},
        "research.tasks.api_query": {"queue": "research"},
        "research.tasks.database_lookup": {"queue": "research"},
        "research.tasks.document_analysis": {"queue": "research"},
        "research.tasks.comparison": {"queue": "research"},
        "research.tasks.troubleshooting": {"queue": "research"},
    },
    # Rate limiting
    task_annotations={
        "research.tasks.web_search": {"rate_limit": "10/m"},
        "research.tasks.api_query": {"rate_limit": "30/m"},
    },
)


def get_task_result(task_id: str) -> dict[str, Any]:
    """Get the result of a research task.

    Args:
        task_id: The Celery task ID

    Returns:
        Dictionary with task status and result
    """
    result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": result.status,
        "result": None,
        "error": None,
    }

    if result.ready():
        if result.successful():
            response["result"] = result.get()
        else:
            response["error"] = str(result.result)

    return response


def revoke_task(task_id: str, terminate: bool = False) -> bool:
    """Revoke a running task.

    Args:
        task_id: The Celery task ID
        terminate: Whether to forcefully terminate the task

    Returns:
        True if task was revoked successfully
    """
    try:
        celery_app.control.revoke(task_id, terminate=terminate)
        return True
    except Exception as e:
        logger.error(f"Failed to revoke task {task_id}: {e}")
        return False


def get_queue_status() -> dict[str, Any]:
    """Get the current status of the research queue.

    Returns:
        Dictionary with queue statistics
    """
    inspector = celery_app.control.inspect()

    stats = {
        "active": inspector.active() or {},
        "scheduled": inspector.scheduled() or {},
        "reserved": inspector.reserved() or {},
        "stats": inspector.stats() or {},
    }

    return stats


@celery_app.task(bind=True)
def update_progress(self, current: int, total: int, message: str = "") -> None:
    """Update task progress.

    Args:
        self: Task instance
        current: Current progress value
        total: Total progress value
        message: Progress message
    """
    self.update_state(
        state="PROGRESS",
        meta={
            "current": current,
            "total": total,
            "message": message,
            "percent": int((current / total) * 100) if total > 0 else 0,
        },
    )
