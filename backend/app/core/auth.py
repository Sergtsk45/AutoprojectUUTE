"""Простая авторизация через API-key для админских эндпоинтов."""

from fastapi import Depends, HTTPException, Query
from fastapi.security import APIKeyHeader

from app.core.config import settings

_api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def verify_admin_key(
    api_key: str | None = Depends(_api_key_header),
    _k: str | None = Query(default=None),
) -> str:
    """Dependency для защиты админских эндпоинтов.

    Ключ: заголовок ``X-Admin-Key`` или query-параметр ``_k`` (fallback, напр. для ссылок).
    Используется точечно на роутерах, НЕ как глобальный middleware.
    """
    key = api_key or _k
    if not key or key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Неверный API-ключ")
    return key
