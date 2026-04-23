"""
Совместимость: публичный API прежнего `app.services.email_service`.

Реализация в пакете `app.services.email` (D2, roadmap §3). Импорты вида
`from app.services.email_service import send_project` остаются валидны.
"""

from __future__ import annotations

from .email import *  # noqa: F403

# Ре-экспорт с тем же `__all__`, что и у `app.services.email`
from .email import __all__  # noqa: F401
