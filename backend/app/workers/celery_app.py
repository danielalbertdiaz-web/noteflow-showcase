"""
Celery application configuration for NoteFlow background tasks.
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "noteflow",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task queues
    task_queues={
        "note_processing": {
            "exchange": "note_processing",
            "routing_key": "note_processing",
        },
        "kinnser_entry": {
            "exchange": "kinnser_entry",
            "routing_key": "kinnser_entry",
        },
    },
    task_default_queue="note_processing",
    # Routes: map task names to queues
    task_routes={
        "app.workers.tasks.process_voice_note": {"queue": "note_processing"},
        "app.workers.tasks.process_text_note": {"queue": "note_processing"},
        "app.workers.tasks.submit_to_kinnser": {"queue": "kinnser_entry"},
    },
    # Retry / reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_max_retries=3,
    # Result expiry (24 hours)
    result_expires=86400,
    # Rate limits
    task_annotations={
        "app.workers.tasks.submit_to_kinnser": {"rate_limit": "10/m"},
    },
    # Worker concurrency: 1 for Kinnser (browser), auto for note processing
    worker_concurrency=4,
)
