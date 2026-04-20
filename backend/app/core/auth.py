"""Простая авторизация через API-key для админских эндпоинтов.

Сравнение ключа выполняется через ``secrets.compare_digest`` для защиты от
timing-атак. Query-параметр ``_k`` оставлен как deprecated fallback для старых
ссылок: при его использовании пишется WARNING в лог, чтобы вычислить и убрать
оставшиеся места. В прод-письмах он уже не используется.
"""

from __future__ import annotations

import logging
import secrets

from fastapi import Depends, HTTPException, Query
from fastapi.security import APIKeyHeader

from app.core.config import settings

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def _mask_key(key: str) -> str:
    """Маскирует ключ для логов: первые 4 символа + длина."""
    if not key:
        return "<empty>"
    return f"{key[:4]}…(len={len(key)})"


async def verify_admin_key(
    api_key: str | None = Depends(_api_key_header),
    _k: str | None = Query(default=None),
) -> str:
    """Dependency для защиты админских эндпоинтов.

    Основной канал — заголовок ``X-Admin-Key``. Query-параметр ``_k`` — deprecated
    fallback на 1 релиз; его использование логируется. Сравнение ключей —
    constant-time (`secrets.compare_digest`).
    """
    expected = settings.admin_api_key

    if api_key:
        provided = api_key
    elif _k:
        logger.warning(
            "deprecated _k query param used for admin auth: %s — переведите клиента на заголовок X-Admin-Key",
            _mask_key(_k),
        )
        provided = _k
    else:
        raise HTTPException(status_code=401, detail="Неверный API-ключ")

    if not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Неверный API-ключ")

    return provided
