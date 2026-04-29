"""
Celery Application Configuration
Configures Celery for background task processing with Redis as broker.
"""

from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "orbit_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.modules.auth.celery_tasks",
        "app.modules.user.celery_tasks",
        "app.modules.orbit_assistant.celery_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Task routing (optional - route specific tasks to specific queues)
celery_app.conf.task_routes = {
    "app.modules.auth.celery_tasks.*": {"queue": "auth"},
    "app.modules.user.celery_tasks.*": {"queue": "user"},
    "app.modules.orbit_assistant.celery_tasks.*": {"queue": "assistant"},
}

# Task rate limits
celery_app.conf.task_annotations = {
    "app.modules.auth.celery_tasks.send_welcome_email": {"rate_limit": "10/m"},
    "app.modules.orbit_assistant.celery_tasks.process_ai_request": {"rate_limit": "30/m"},
}
