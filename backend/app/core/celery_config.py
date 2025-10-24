from celery.schedules import crontab

beat_schedule = {
    "monitor-devices": {
        "task": "app.worker.poll_devices",
        "schedule": crontab(minute="*/3"),  # Cada 3 minutos
    },
}

task_routes = {
    "app.worker.poll_devices": "monitor",
}

task_time_limit = 300  # 5 minutos máximo por tarea
task_soft_time_limit = 240  # Aviso a los 4 minutos

# Configuración de reintentos con backoff exponencial
task_acks_late = True
task_reject_on_worker_lost = True
task_max_retries = 3
task_retry_delay = 60  # 1 minuto inicial
task_retry_backoff = True
task_retry_backoff_max = 600  # Máximo 10 minutos entre reintentos