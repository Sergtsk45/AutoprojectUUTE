"""Эндпоинты для работы с email: предпросмотр, ручная отправка, лог."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_admin_key
from app.core.database import get_db
from app.models import OrderStatus, EmailType
from app.schemas import EmailLogResponse
from app.services import OrderService

router = APIRouter(prefix="/emails", tags=["emails"], dependencies=[Depends(verify_admin_key)])


def get_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(db)


# ── Предпросмотр писем (для отладки) ────────────────────────────────────────


@router.get(
    "/{order_id}/preview/info-request",
    response_class=HTMLResponse,
    summary="Предпросмотр письма «Запрос документов»",
)
async def preview_info_request(
    order_id: uuid.UUID,
    svc: OrderService = Depends(get_service),
):
    from app.services.email_service import render_info_request

    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    subject, html_body, _ = render_info_request(order)
    return HTMLResponse(content=html_body)


@router.get(
    "/{order_id}/preview/reminder",
    response_class=HTMLResponse,
    summary="Предпросмотр письма-напоминания",
)
async def preview_reminder(
    order_id: uuid.UUID,
    svc: OrderService = Depends(get_service),
):
    from app.services.email_service import render_reminder

    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    subject, html_body, _ = render_reminder(order)
    return HTMLResponse(content=html_body)


@router.get(
    "/{order_id}/preview/project-delivery",
    response_class=HTMLResponse,
    summary="Предпросмотр письма «Проект готов»",
)
async def preview_project_delivery(
    order_id: uuid.UUID,
    svc: OrderService = Depends(get_service),
):
    from app.services.email_service import render_project_delivery

    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    subject, html_body, _ = render_project_delivery(order)
    return HTMLResponse(content=html_body)


# ── Ручная отправка (админка) ────────────────────────────────────────────────


class ManualSendRequest(BaseModel):
    email_type: EmailType
    error_description: str | None = None
    action_required: str | None = None


class ManualSendResponse(BaseModel):
    success: bool
    message: str


@router.post(
    "/{order_id}/send",
    response_model=ManualSendResponse,
    summary="Ручная отправка письма (админка)",
)
async def manual_send_email(
    order_id: uuid.UUID,
    data: ManualSendRequest,
    svc: OrderService = Depends(get_service),
):
    """Ручная отправка письма по заявке.

    Полезно для:
    - повторной отправки, если автоматическая не дошла
    - отправки уведомления об ошибке с кастомным текстом
    """
    from app.services.email_service import (
        has_successful_email,
        send_info_request,
        send_reminder,
        send_project,
        send_error_notification,
    )

    # Используем синхронную сессию, т.к. email_service синхронный
    from app.services.tasks import SyncSession

    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    with SyncSession() as sync_session:
        # Перезагружаем order в синхронной сессии
        from app.services.tasks import _get_order

        sync_order = _get_order(sync_session, order_id)
        if sync_order is None:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        if data.email_type == EmailType.INFO_REQUEST:
            if has_successful_email(sync_session, order_id, EmailType.INFO_REQUEST):
                raise HTTPException(
                    status_code=409,
                    detail="Запрос клиенту уже отправлялся",
                )
            success = send_info_request(sync_session, sync_order)
        elif data.email_type == EmailType.REMINDER:
            if has_successful_email(sync_session, order_id, EmailType.REMINDER):
                raise HTTPException(
                    status_code=409,
                    detail="Напоминание уже отправлялось",
                )
            success = send_reminder(sync_session, sync_order)
        elif data.email_type == EmailType.PROJECT_DELIVERY:
            success = send_project(sync_session, sync_order)
        elif data.email_type == EmailType.ERROR_NOTIFICATION:
            success = send_error_notification(
                sync_session,
                sync_order,
                error_description=data.error_description or "Ошибка при обработке заявки",
                action_required=data.action_required,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Неизвестный тип: {data.email_type}")

    return ManualSendResponse(
        success=success,
        message="Письмо отправлено" if success else "Ошибка отправки, см. логи",
    )


# ── Лог писем ────────────────────────────────────────────────────────────────


@router.get(
    "/{order_id}/log",
    response_model=list[EmailLogResponse],
    summary="Лог отправленных писем по заявке",
)
async def get_email_log(
    order_id: uuid.UUID,
    svc: OrderService = Depends(get_service),
):
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return order.emails
