"""Celery Beat periodic reminders (D1.b)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.models import EmailType, Order, OrderStatus

from ._common import (
    FINAL_PAYMENT_REMINDER_DELAY_DAYS,
    SyncSession,
    _has_successful_final_payment_reminder,
)

logger = logging.getLogger(__name__)


@celery_app.task(name="app.services.tasks.send_final_payment_reminders_after_rso_scan")
def send_final_payment_reminders_after_rso_scan():
    """Напоминание об остатке спустя 15 дней после загрузки скана в РСО."""
    from datetime import datetime, timedelta, timezone

    from app.services.email_service import send_final_payment_request

    logger.info(
        "send_final_payment_reminders_after_rso_scan: проверка заявок после загрузки скана РСО"
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=FINAL_PAYMENT_REMINDER_DELAY_DAYS)
    sent_count = 0

    with SyncSession() as session:
        orders = list(
            session.execute(
                select(Order)
                .options(selectinload(Order.emails))
                .where(Order.status == OrderStatus.AWAITING_FINAL_PAYMENT)
                .where(Order.rso_scan_received_at.isnot(None))
                .where(Order.rso_scan_received_at <= cutoff)
                .where(Order.final_paid_at.is_(None))
            )
            .scalars()
            .all()
        )

        for order in orders:
            if _has_successful_final_payment_reminder(session, order.id, "rso_scan_15d"):
                continue

            success = send_final_payment_request(
                session,
                order,
                retry_count=order.retry_count,
                post_rso_scan=True,
                reminder_kind="rso_scan_15d",
            )
            if success:
                sent_count += 1
                logger.info(
                    "send_final_payment_reminders_after_rso_scan: напоминание отправлено order=%s",
                    order.id,
                )

    logger.info(
        "send_final_payment_reminders_after_rso_scan: отправлено %d напоминаний",
        sent_count,
    )


@celery_app.task(name="app.services.tasks.send_reminders")
def send_reminders():
    """Периодическая задача: одно напоминание клиенту после успешного info_request.

    Условия: WAITING_CLIENT_INFO, уже был успешный info_request, успешного reminder ещё не было,
    с момента последнего успешного info_request прошло не менее 3 суток, retry_count < max_retry_count.
    """
    from datetime import datetime, timedelta, timezone

    from app.services.email_service import has_successful_email, send_reminder

    logger.info("send_reminders: проверка заявок, ожидающих ответа клиента")

    with SyncSession() as session:
        stmt = (
            select(Order)
            .options(selectinload(Order.emails))
            .where(Order.status == OrderStatus.WAITING_CLIENT_INFO)
            .where(Order.retry_count < settings.max_retry_count)
        )
        orders = list(session.execute(stmt).scalars().all())

        cutoff = datetime.now(timezone.utc) - timedelta(days=3)
        sent_count = 0

        for order in orders:
            if not has_successful_email(session, order.id, EmailType.INFO_REQUEST):
                continue
            if has_successful_email(session, order.id, EmailType.REMINDER):
                logger.debug(
                    "send_reminders: пропуск order=%s — напоминание уже отправлялось",
                    order.id,
                )
                continue

            last_info = max(
                (
                    e.sent_at
                    for e in order.emails
                    if e.email_type == EmailType.INFO_REQUEST and e.sent_at is not None
                ),
                default=None,
            )
            if last_info is None:
                continue
            last_info_utc = last_info.replace(tzinfo=timezone.utc)
            if last_info_utc > cutoff:
                continue

            success = send_reminder(session, order)
            if success:
                order.retry_count += 1
                session.commit()
                sent_count += 1
                logger.info(
                    "Напоминание отправлено: order=%s, попытка %d",
                    order.id,
                    order.retry_count,
                )

        logger.info("send_reminders: отправлено %d напоминаний", sent_count)
