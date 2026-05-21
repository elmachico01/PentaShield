from celery import Celery

from backend.config import get_settings

settings = get_settings()

celery_app = Celery(
    "pentashield",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.workers.test_worker", "backend.workers.recon_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Rome",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
