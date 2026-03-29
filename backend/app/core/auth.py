"""Простая авторизация через API-key для админских эндпоинтов."""

from fastapi import HTTPException, Depends
from fastapi.security import APIKeyHeader

from app.core.config import settings

_api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def verify_admin_key(api_key: str | None = Depends(_api_key_header)) -> str:
    """Dependency для защиты админских эндпоинтов.

    Используется точечно на роутерах, НЕ как глобальный middleware.
    """
    if not api_key or api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Неверный API-ключ")
    return api_key
