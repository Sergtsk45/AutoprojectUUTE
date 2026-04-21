"""Эндпоинты для работы с парсингом ТУ: просмотр результатов, ручной перезапуск."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_admin_key
from app.core.database import get_db
from app.models import OrderStatus
from app.repositories.order_jsonb import (
    get_parsed_params,
    get_parsed_params_dict,
    set_parsed_params,
)
from app.services import OrderService

router = APIRouter(prefix="/parsing", tags=["parsing"], dependencies=[Depends(verify_admin_key)])


def get_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(db)


class ParsedDataResponse(BaseModel):
    """Результат парсинга ТУ."""

    order_id: uuid.UUID
    status: str
    parsed_params: dict | None
    missing_params: list | None
    parse_confidence: float | None
    warnings: list | None


@router.get(
    "/{order_id}/result",
    response_model=ParsedDataResponse,
    summary="Результат парсинга ТУ",
)
async def get_parsing_result(
    order_id: uuid.UUID,
    svc: OrderService = Depends(get_service),
):
    """Просмотр извлечённых параметров из ТУ.

    Возвращает parsed_params, missing_params, confidence и warnings.
    Доступно после перехода в статус tu_parsed.
    """
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    # Валидируем через accessor (невалидные исторические данные → {} + WARNING).
    parsed = get_parsed_params(order)
    params = get_parsed_params_dict(order)

    return ParsedDataResponse(
        order_id=order.id,
        status=order.status.value,
        parsed_params=params or None,
        missing_params=order.missing_params,
        parse_confidence=parsed.parse_confidence if parsed else None,
        warnings=list(parsed.warnings) if parsed else None,
    )


class RetriggerResponse(BaseModel):
    message: str
    task_id: str | None = None


@router.post(
    "/{order_id}/retrigger",
    response_model=RetriggerResponse,
    summary="Перезапустить парсинг ТУ",
)
async def retrigger_parsing(
    order_id: uuid.UUID,
    svc: OrderService = Depends(get_service),
):
    """Перезапустить парсинг ТУ.

    Полезно если:
    - Первый парсинг дал низкий confidence
    - LLM-сервис был недоступен
    - Загружен новый файл ТУ
    """
    from app.services.tasks import start_tu_parsing

    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    allowed = {
        OrderStatus.TU_PARSING,
        OrderStatus.TU_PARSED,
        OrderStatus.ERROR,
    }
    if order.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Перезапуск парсинга недоступен в статусе {order.status.value}",
        )

    # Сбрасываем в NEW, чтобы пройти переход корректно
    order.status = OrderStatus.NEW
    set_parsed_params(order, None)
    order.missing_params = []
    db = svc.db
    await db.commit()

    task = start_tu_parsing.delay(str(order_id))

    return RetriggerResponse(
        message="Парсинг перезапущен",
        task_id=task.id,
    )
