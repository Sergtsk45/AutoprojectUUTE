"""D4 smoke: async-роутеры не содержат ``SyncSession()`` и корректно выносят
блокирующую работу в Celery / ``asyncio.to_thread``."""

from __future__ import annotations

import os
import pathlib
import re
import uuid
from unittest.mock import patch

os.environ.setdefault("ADMIN_API_KEY", "test")
os.environ.setdefault("SMTP_PASSWORD", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("CORS_ORIGINS", '["https://example.com"]')
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/d")


_API_DIR = pathlib.Path(__file__).resolve().parents[1] / "app" / "api"
_SYNC_SESSION_RE = re.compile(r"SyncSession\(\)")


def test_no_sync_session_in_async_routers() -> None:
    """CI-гуард: `SyncSession()` запрещён в `backend/app/api/` (audit D4)."""
    offenders: list[str] = []
    for py in _API_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if _SYNC_SESSION_RE.search(text):
            offenders.append(str(py.relative_to(_API_DIR.parents[1])))
    assert not offenders, (
        "SyncSession() найден в async-роутерах: "
        f"{offenders}. Вынесите sync-работу в Celery-задачу или app/services/*."
    )


def test_notify_engineer_new_order_registered() -> None:
    """Новая Celery-задача зарегистрирована под стабильным именем."""
    from app.core.celery_app import celery_app

    import app.services.tasks  # noqa: F401 — side-effect: регистрация задач

    assert "app.services.tasks.notify_engineer_new_order" in celery_app.tasks


def test_manual_send_email_sync_404() -> None:
    """`manual_send_email_sync` бросает ManualSendError(404) при отсутствии заявки."""
    from app.models.models import EmailType
    from app.services.email import ManualSendError, manual_send_email_sync

    class _Session:
        def __enter__(self) -> _Session:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    with (
        patch("app.services.tasks.SyncSession", return_value=_Session()),
        patch("app.services.tasks._get_order", return_value=None),
    ):
        try:
            manual_send_email_sync(
                uuid.uuid4(),
                EmailType.INFO_REQUEST,
                None,
                None,
            )
        except ManualSendError as exc:
            assert exc.status_code == 404
        else:  # pragma: no cover — защитимся от молчаливого прохода
            raise AssertionError("Ожидался ManualSendError(404), но исключения не было")
