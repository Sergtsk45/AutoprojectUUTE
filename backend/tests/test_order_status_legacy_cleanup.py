"""Smoke: после C1/C2 enum `OrderStatus` не содержит legacy-значений.

Фаза C1+C2 аудита (2026-04-22). Удалены `data_complete`, `generating_project`,
`review`. Тест проверяет, что они не вернутся случайно при мерже или
при ручном редактировании `models.py` и `ALLOWED_TRANSITIONS`.
"""

from __future__ import annotations

import os

os.environ.setdefault("ADMIN_API_KEY", "test")
os.environ.setdefault("SMTP_PASSWORD", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("CORS_ORIGINS", '["https://example.com"]')
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/d")


_REMOVED_STATUS_VALUES = frozenset({"data_complete", "generating_project", "review"})


def test_order_status_enum_has_no_legacy_values() -> None:
    from app.models.models import OrderStatus

    actual = {member.value for member in OrderStatus}
    leftover = actual & _REMOVED_STATUS_VALUES
    assert not leftover, f"Legacy OrderStatus значения не удалены: {leftover}"


def test_allowed_transitions_have_no_legacy_references() -> None:
    from app.models.models import ALLOWED_TRANSITIONS

    all_values = {
        member.value
        for source, targets in ALLOWED_TRANSITIONS.items()
        for member in (source, *targets)
    }
    leftover = all_values & _REMOVED_STATUS_VALUES
    assert not leftover, f"ALLOWED_TRANSITIONS всё ещё ссылается на legacy-статусы: {leftover}"


def test_legacy_task_attributes_are_removed() -> None:
    """`fill_excel`, `generate_project`, `initiate_payment_flow` — удалены."""
    import app.services.tasks as tasks_pkg

    for legacy in ("fill_excel", "generate_project", "initiate_payment_flow"):
        assert not hasattr(tasks_pkg, legacy), (
            f"app.services.tasks всё ещё экспортирует legacy-task {legacy!r}"
        )
