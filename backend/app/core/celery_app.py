from celery import Celery
from app.core.config import settings
from app.core.celery_config import beat_schedule

celery_app = Celery(
    "worker",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
)

celery_app.conf.task_routes = {
    "app.worker.monitor_devices": "main-queue",
    "app.worker.analyze_device_logs_with_ai": "main-queue",
    "app.worker.cleanup_old_alerts": "main-queue",
}

celery_app.conf.beat_schedule = beat_schedule