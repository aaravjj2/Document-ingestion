"""Celery application configuration."""

from celery import Celery

from src.core.config import settings

# Create Celery app
celery_app = Celery(
    "document_ingestion",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.workers.tasks"],
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # Soft limit 9 minutes
    
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
    
    # Result settings
    result_expires=86400,  # Results expire after 24 hours
    
    # Rate limiting
    task_default_rate_limit="10/m",  # 10 tasks per minute default
    
    # Retry settings
    task_default_retry_delay=30,  # 30 seconds between retries
    task_max_retries=3,
)

# Task routes (optional - for multi-queue setup)
celery_app.conf.task_routes = {
    "src.workers.tasks.process_document": {"queue": "document_processing"},
    "src.workers.tasks.*": {"queue": "default"},
}
