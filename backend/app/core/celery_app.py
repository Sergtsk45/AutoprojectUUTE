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
    # Гарантии доставки (audit D5):
    # acks_late=True — задача подтверждается только после успешного выполнения
    #                  (при OOM/SIGKILL воркера сообщение возвращается в очередь).
    # reject_on_worker_lost=True — Redis-broker сам переотдаст задачу другому
    #                  воркеру при потере соединения (вместо тихой потери).
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # D5: visibility_timeout снижен с 24 ч до 1 ч.
    # Раньше нужен был 86400 с под `apply_async(countdown=86400)` для info_request,
    # но эта схема убрана: отложенные info_request теперь ставит исключительно
    # Beat-джоба `process_due_info_requests` (каждые 5 мин), а не sleep в очереди.
    # Длинный visibility_timeout приводил к тому, что любая acks_late-задача,
    # которую воркер не успевал подтвердить, висела сутки — заменили на 1 ч.
    broker_transport_options={"visibility_timeout": 3600},
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
            # D5: было `*/15`. Снизили до 5 мин, т.к. это единственный источник
            # отложенного info_request (раньше был ещё точечный `apply_async(countdown=86400)`).
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "default"},
        },
        "send-final-payment-reminders-after-rso-scan": {
            "task": "app.services.tasks.send_final_payment_reminders_after_rso_scan",
            "schedule": crontab(hour=10, minute=15),
            "options": {"queue": "default"},
        },
    },
)

celery_app.autodiscover_tasks(["app.services"])
