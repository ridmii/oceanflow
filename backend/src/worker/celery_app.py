"""
src/worker/celery_app.py
========================
Celery application definition.
"""

from celery import Celery
from celery.signals import setup_logging
from src.settings import settings

@setup_logging.connect
def config_loggers(*args, **kwargs):
    from src.api.logging import setup_logging as custom_setup_logging
    custom_setup_logging()

celery_app = Celery(
    "oceanflow",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,           # 24 hours
    broker_connection_retry_on_startup=True,
)

celery_app.autodiscover_tasks(["src.worker"])
