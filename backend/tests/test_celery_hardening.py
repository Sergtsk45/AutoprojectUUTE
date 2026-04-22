"""D5 smoke: гарантии доставки Celery (`acks_late`, `reject_on_worker_lost`,
`visibility_timeout`) и единственный источник отложенного info_request — Beat-джоба."""

from __future__ import annotations

import os

os.environ.setdefault("ADMIN_API_KEY", "test")
os.environ.setdefault("SMTP_PASSWORD", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("CORS_ORIGINS", '["https://example.com"]')
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/d")


def test_celery_hardening_settings() -> None:
    """visibility_timeout=3600, acks_late+reject_on_worker_lost — оба True."""
    from app.core.celery_app import celery_app

    conf = celery_app.conf

    assert conf.task_acks_late is True, "task_acks_late должен быть True"
    assert conf.task_reject_on_worker_lost is True, (
        "task_reject_on_worker_lost должен быть True (audit D5)"
    )

    visibility_timeout = (conf.broker_transport_options or {}).get("visibility_timeout")
    assert visibility_timeout == 3600, (
        f"broker_transport_options['visibility_timeout'] ожидался 3600, "
        f"получен {visibility_timeout!r}. После D5 24-часовых countdown больше нет."
    )


def test_no_long_countdown_apply_async() -> None:
    """Регрессия: в коде backend/app/ не должно быть `countdown=86400` или эквивалентов.

    Раньше `apply_async(countdown=86400)` форсировал `visibility_timeout=86400`.
    После D5 такие вызовы запрещены.
    """
    import pathlib
    import re

    backend_app = pathlib.Path(__file__).resolve().parents[1] / "app"
    pattern = re.compile(r"countdown\s*=\s*(86400|24\s*\*\s*60\s*\*\s*60)")

    offenders: list[str] = []
    for py in backend_app.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            # Пропускаем комментарии и строки с упоминанием в docstring/исторический
            # текст — но если выражение реально вычислится, ловим. В живом коде
            # этого паттерна быть не должно (audit D5).
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                offenders.append(f"{py.relative_to(backend_app.parent)}:{line_no}: {stripped}")

    assert not offenders, (
        "Найдены countdown=86400 в backend/app/ (audit D5 запрещает): "
        f"{offenders}. Используйте Beat-джобу process_due_info_requests."
    )


def test_process_due_info_requests_in_beat_schedule() -> None:
    """`process_due_info_requests` остаётся в Beat и работает чаще, чем раньше."""
    from app.core.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    assert "process-due-info-requests" in schedule, (
        "Beat-джоба process-due-info-requests должна остаться: это единственный "
        "источник отложенного info_request после D5."
    )
    entry = schedule["process-due-info-requests"]
    assert entry["task"] == "app.services.tasks.process_due_info_requests"
