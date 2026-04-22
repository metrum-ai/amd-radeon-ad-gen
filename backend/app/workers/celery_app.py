# Created by Metrum AI for AMD

from app.config import settings
from celery import Celery
from celery.schedules import crontab

celery = Celery(
    "adgen",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

celery.conf.update(
    include=[
        "app.workers.tasks.strategy",
        "app.workers.tasks.image_gen",
        "app.workers.tasks.quality_gate",
        "app.workers.tasks.compositor",
        "app.workers.tasks.audio_gen",
        "app.workers.tasks.video_gen",
        "app.workers.tasks.finalize",
        "app.workers.tasks.export",
    ]
)

celery.conf.beat_schedule = {
    "cleanup-stuck-campaigns": {
        "task": "app.workers.tasks.finalize.cleanup_stuck_campaigns",
        "schedule": crontab(minute="*/10"),
    },
}
