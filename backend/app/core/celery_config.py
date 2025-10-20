from celery.schedules import crontab

beat_schedule = {
    "monitor-devices-every-15-minutes": {
        "task": "app.worker.monitor_devices",
        "schedule": crontab(minute="*/15"),
    },
    "cleanup-old-alerts-daily": {
        "task": "app.worker.cleanup_old_alerts",
        "schedule": crontab(hour=3, minute=0),  # 3:00 AM
        "kwargs": {"days": 30},
    },
}