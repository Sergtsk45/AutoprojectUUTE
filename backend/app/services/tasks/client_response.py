"""Info_request, process_client, beat, engineer notifications (D1.b)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.models import EmailType, FileCategory, Order, OrderStatus
from app.services.param_labels import compute_client_document_missing

from ._common import SyncSession, _get_order, _transition

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.services.tasks.send_info_request_email",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def send_info_request_email(self, order_id: str):
    """Отправка письма клиенту с запросом недостающей информации.

    Вызывается:
    - по таймеру: apply_async(..., countdown=INFO_REQUEST_AUTO_DELAY_SECONDS) из check_data_completeness;
    - резервно: process_due_info_requests (Beat), если отложенная задача не отработала.

    Идемпотентна: не шлёт дубликат при ручной отправке инженером ранее.
    """
    from datetime import datetime, timedelta, timezone

    from app.services.email_service import has_successful_email, send_info_request

    oid = uuid.UUID(order_id)
    logger.info("send_info_request_email: order=%s", oid)

    with SyncSession() as session:
        # SELECT FOR UPDATE блокирует строку на уровне БД: если несколько воркеров
        # стартуют одновременно, второй воркер ждёт снятия блокировки первым.
        # После разблокировки has_successful_email уже видит запись в EmailLog
        # от первого воркера и пропускает повторную отправку.
        # Блокировка удерживается до session.commit() в конце функции.
        order = session.execute(
            select(Order)
            .options(selectinload(Order.files), selectinload(Order.emails))
            .where(Order.id == oid)
            .with_for_update()
        ).scalar_one_or_none()

        if order is None:
            return

        if order.status != OrderStatus.WAITING_CLIENT_INFO:
            logger.info(
                "send_info_request_email: пропуск order=%s — статус %s",
                oid,
                order.status,
            )
            return

        if has_successful_email(session, oid, EmailType.INFO_REQUEST):
            logger.info(
                "send_info_request_email: пропуск order=%s — запрос уже отправлялся",
                oid,
            )
            return

        if order.waiting_client_info_at is None:
            logger.info(
                "send_info_request_email: пропуск order=%s — нет waiting_client_info_at",
                oid,
            )
            return

        due = order.waiting_client_info_at + timedelta(hours=24)
        if datetime.now(timezone.utc) < due:
            logger.info(
                "send_info_request_email: пропуск order=%s — ещё не наступил срок (%s)",
                oid,
                due.isoformat(),
            )
            return

        success = send_info_request(session, order)

        if success:
            order.retry_count += 1
            session.commit()
            logger.info(
                "Письмо с запросом отправлено на %s (попытка %d)",
                order.client_email,
                order.retry_count,
            )
        else:
            logger.error("Не удалось отправить письмо на %s", order.client_email)
            try:
                self.retry()
            except self.MaxRetriesExceededError:
                logger.error("Исчерпаны попытки отправки email для order=%s", oid)


@celery_app.task(name="app.services.tasks.process_due_info_requests")
def process_due_info_requests():
    """Периодически: заявки в WAITING_CLIENT_INFO старше 24 ч без успешного info_request."""
    from datetime import datetime, timedelta, timezone

    from app.services.email_service import has_successful_email

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    orders: list[Order] = []
    queued = 0

    with SyncSession() as session:
        stmt = (
            select(Order)
            .options(selectinload(Order.emails))
            .where(Order.status == OrderStatus.WAITING_CLIENT_INFO)
            .where(Order.waiting_client_info_at.isnot(None))
            .where(Order.waiting_client_info_at <= cutoff)
        )
        orders = list(session.execute(stmt).scalars().all())
        queued = 0
        for order in orders:
            if has_successful_email(session, order.id, EmailType.INFO_REQUEST):
                continue
            logger.info(
                "process_due_info_requests: очередь info_request для order=%s",
                order.id,
            )
            send_info_request_email.delay(str(order.id))
            queued += 1

    logger.info(
        "process_due_info_requests: кандидатов %d, поставлено в очередь %d",
        len(orders),
        queued,
    )


@celery_app.task(name="app.services.tasks.notify_engineer_new_order")
def notify_engineer_new_order(
    order_id: str,
    *,
    circuits: int | None = None,
    price: int | None = None,
    order_type: str | None = None,
) -> None:
    """Уведомляет инженера о новой заявке (fire-and-forget из async-роутера).

    D4: заменяет синхронный `SyncSession()`+SMTP внутри `POST /landing/order`.
    Event loop не блокируется; при падении SMTP письмо просто не уходит,
    заявка всё равно считается созданной (поведение совпадает с прежним
    `try/except` в роутере).
    """
    from app.services.email_service import send_new_order_notification

    oid = uuid.UUID(order_id)
    logger.info("notify_engineer_new_order: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            logger.warning("notify_engineer_new_order: order %s не найден", oid)
            return
        send_new_order_notification(
            session,
            order,
            circuits=circuits,
            price=price,
            order_type=order_type,
        )


@celery_app.task(name="app.services.tasks.notify_engineer_tu_parsed")
def notify_engineer_tu_parsed(order_id: str):
    """Уведомляет инженера после успешного парсинга загруженного ТУ."""
    from app.services.email_service import send_tu_parsed_notification

    oid = uuid.UUID(order_id)
    logger.info("notify_engineer_tu_parsed: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return
        send_tu_parsed_notification(session, order)


@celery_app.task(name="app.services.tasks.notify_engineer_client_documents_received")
def notify_engineer_client_documents_received(order_id: str):
    """Уведомляет инженера каждый раз, когда клиент отправляет документы."""
    from app.services.email_service import send_client_documents_received_notification

    oid = uuid.UUID(order_id)
    logger.info("notify_engineer_client_documents_received: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return
        send_client_documents_received_notification(session, order)


@celery_app.task(name="app.services.tasks.process_client_response", bind=True)
def process_client_response(self, order_id: str):
    """CLIENT_INFO_RECEIVED: Обработка ответа клиента.

    Вызывается после того, как клиент загрузил файлы
    через страницу upload-page.
    """
    oid = uuid.UUID(order_id)
    logger.info("process_client_response: order=%s", oid)

    from datetime import datetime, timezone

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return
        if order.status not in (
            OrderStatus.CLIENT_INFO_RECEIVED,
            OrderStatus.WAITING_CLIENT_INFO,
        ):
            logger.warning(
                "process_client_response: order=%s в статусе %s, пропускаем",
                oid,
                order.status.value,
            )
            return

        uploaded_categories = {f.category.value for f in order.files}
        missing = compute_client_document_missing(uploaded_categories)
        if (
            FileCategory.COMPANY_CARD.value not in uploaded_categories
            and FileCategory.COMPANY_CARD.value not in missing
        ):
            missing.append(FileCategory.COMPANY_CARD.value)
        order.missing_params = missing
        session.commit()

        if FileCategory.COMPANY_CARD.value not in uploaded_categories:
            order.waiting_client_info_at = datetime.now(timezone.utc)
            session.commit()
            if order.status != OrderStatus.WAITING_CLIENT_INFO:
                _transition(session, order, OrderStatus.WAITING_CLIENT_INFO)
            logger.info(
                "process_client_response: company_card не загружен, order=%s возвращён в waiting_client_info",
                oid,
            )
            return

    from . import contract_flow

    contract_flow.process_card_and_contract.delay(order_id)
