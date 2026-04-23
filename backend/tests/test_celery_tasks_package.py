"""Smoke: после D1.b пакет app.services.tasks регистрирует все задачи под именами D1.a."""

from __future__ import annotations

import os

# Минимум env для import settings при загрузке celery
os.environ.setdefault("ADMIN_API_KEY", "test")
os.environ.setdefault("SMTP_PASSWORD", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("CORS_ORIGINS", '["https://example.com"]')
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/d")


def test_all_task_names_registered() -> None:
    from app.core.celery_app import celery_app

    import app.services.tasks  # noqa: F401 — side-effect: регистрация задач

    expected = {
        "app.services.tasks.start_tu_parsing",
        "app.services.tasks.check_data_completeness",
        "app.services.tasks.send_info_request_email",
        "app.services.tasks.process_due_info_requests",
        "app.services.tasks.notify_engineer_new_order",
        "app.services.tasks.notify_engineer_tu_parsed",
        "app.services.tasks.notify_engineer_client_documents_received",
        "app.services.tasks.process_client_response",
        "app.services.tasks.process_card_and_contract",
        "app.services.tasks.send_completed_project",
        "app.services.tasks.process_advance_payment",
        "app.services.tasks.process_final_payment",
        "app.services.tasks.resend_corrected_project",
        "app.services.tasks.parse_company_card_task",
        "app.services.tasks.process_company_card_and_send_contract",
        "app.services.tasks.notify_engineer_rso_scan_received",
        "app.services.tasks.notify_engineer_rso_remarks_received",
        "app.services.tasks.notify_client_after_rso_scan",
        "app.services.tasks.notify_engineer_signed_contract",
        "app.services.tasks.send_final_payment_reminders_after_rso_scan",
        "app.services.tasks.send_reminders",
    }
    registered = {k for k in celery_app.tasks.keys() if k.startswith("app.services.tasks.")}
    missing = expected - registered
    extra = registered - expected
    assert not missing, f"Не зарегистрированы: {missing}"
    assert not extra, f"Лишние (удалить из expected или расследовать): {extra}"
