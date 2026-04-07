from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "uute_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    # Повторные попытки при падении воркера
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Автообнаружение задач
    task_routes={
        "app.services.tasks.*": {"queue": "default"},
    },
    # Периодические задачи (Celery Beat)
    beat_schedule={
        "send-reminders-daily": {
            "task": "app.services.tasks.send_reminders",
            "schedule": crontab(hour=10, minute=0),  # Каждый день в 10:00 МСК
            "options": {"queue": "default"},
        },
        "process-due-info-requests": {
            "task": "app.services.tasks.process_due_info_requests",
            "schedule": crontab(minute="*/15"),
            "options": {"queue": "default"},
        },
    },
)

celery_app.autodiscover_tasks(["app.services"])
