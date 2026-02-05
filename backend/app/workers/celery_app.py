"""
Celery application configuration for async task processing.
"""

from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "c_ocr_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.document_tasks",
        "app.workers.ocr_tasks",
        "app.workers.template_tasks",
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Optional: Configure task routes
celery_app.conf.task_routes = {
    "app.workers.document_tasks.*": {"queue": "documents"},
    "app.workers.ocr_tasks.*": {"queue": "ocr"},
    "app.workers.template_tasks.*": {"queue": "templates"},
}

if __name__ == "__main__":
    celery_app.start()
