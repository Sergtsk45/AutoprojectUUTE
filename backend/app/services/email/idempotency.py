"""
* @file: idempotency.py
* @description: Проверка успешных отправок и запись в email_log.
* @dependencies: app.models.models (EmailLog, EmailType, Order)
* @created: 2026-04-22
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import EmailLog, EmailType, Order


def has_successful_email(
    session: Session,
    order_id: uuid.UUID,
    email_type: EmailType,
) -> bool:
    """True, если по заявке уже есть успешная отправка данного типа (sent_at задан)."""
    stmt = (
        select(EmailLog.id)
        .where(
            EmailLog.order_id == order_id,
            EmailLog.email_type == email_type,
            EmailLog.sent_at.isnot(None),
        )
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none() is not None


def log_email(
    session: Session,
    order: Order,
    email_type: EmailType,
    subject: str,
    body: str,
    success: bool,
    error_msg: str | None = None,
) -> EmailLog:
    """Создаёт запись в email_log (клиентское письмо по заявке)."""
    log = EmailLog(
        order_id=order.id,
        email_type=email_type,
        recipient=order.client_email,
        subject=subject,
        body_text=body[:5000],
        sent_at=datetime.now(timezone.utc) if success else None,
        error_message=error_msg,
    )
    session.add(log)
    session.commit()
    return log
