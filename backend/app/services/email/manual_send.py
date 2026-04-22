"""
* @file: manual_send.py
* @description: Синхронный хелпер для ручной отправки письма (admin endpoint,
*               выполняется через asyncio.to_thread в `app/api/emails.py`, D4).
* @dependencies: .service, .idempotency, app.services.tasks._common
* @created: 2026-04-22
"""

from __future__ import annotations

import uuid

from app.models.models import EmailType


class ManualSendError(Exception):
    """Исключение с HTTP-кодом/detail для transport-level конверсии в HTTPException.

    Бросается из `manual_send_email_sync`; async-роутер перехватывает и
    превращает в `HTTPException(status_code=..., detail=...)`.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def manual_send_email_sync(
    order_id: uuid.UUID,
    email_type: EmailType,
    error_description: str | None,
    action_required: str | None,
) -> bool:
    """Открывает синхронную сессию, выбирает нужный `send_*` и отправляет письмо.

    Инкапсулирует всю блокирующую работу (SyncSession + SMTP). Бросает
    :class:`ManualSendError` при функциональных ошибках (404/409/400).
    Возвращает флаг успеха SMTP.
    """
    from app.services.email_service import (
        has_successful_email,
        send_error_notification,
        send_info_request,
        send_project,
        send_reminder,
    )
    from app.services.tasks import SyncSession, _get_order

    with SyncSession() as sync_session:
        sync_order = _get_order(sync_session, order_id)
        if sync_order is None:
            raise ManualSendError(status_code=404, detail="Заявка не найдена")

        if email_type == EmailType.INFO_REQUEST:
            if has_successful_email(sync_session, order_id, EmailType.INFO_REQUEST):
                raise ManualSendError(
                    status_code=409,
                    detail="Запрос клиенту уже отправлялся",
                )
            return send_info_request(sync_session, sync_order)

        if email_type == EmailType.REMINDER:
            if has_successful_email(sync_session, order_id, EmailType.REMINDER):
                raise ManualSendError(
                    status_code=409,
                    detail="Напоминание уже отправлялось",
                )
            return send_reminder(sync_session, sync_order)

        if email_type == EmailType.PROJECT_DELIVERY:
            return send_project(sync_session, sync_order)

        if email_type == EmailType.ERROR_NOTIFICATION:
            return send_error_notification(
                sync_session,
                sync_order,
                error_description=error_description or "Ошибка при обработке заявки",
                action_required=action_required,
            )

        raise ManualSendError(status_code=400, detail=f"Неизвестный тип: {email_type}")
