"""Post-project delivery, RSO notifications (D1.b)."""

from __future__ import annotations

import logging
import uuid
from html import escape
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.models import FileCategory, Order, OrderStatus, EmailType

from ._common import (
    SyncSession,
    _collect_project_attachments,
    _ensure_completion_act_attachment,
    _ensure_final_invoice_attachment,
    _existing_order_file_path,
    _get_order,
    _has_successful_final_payment_reminder,
    _latest_order_file,
    _transition,
)

logger = logging.getLogger(__name__)


def _send_post_project_delivery(
    session: Session,
    order: Order,
    *,
    is_redelivery: bool,
) -> tuple[bool, list[Path]]:
    """Отправляет клиенту проект, сопроводительное и сохранённый счёт на остаток."""
    from app.services.email_service import send_project, send_project_redelivery

    temporary_paths: list[Path] = []
    attachment_paths, cover_letter_path = _collect_project_attachments(session, order)
    if cover_letter_path is not None:
        temporary_paths.append(cover_letter_path)

    final_invoice_path, temp_invoice_path = _ensure_final_invoice_attachment(session, order)
    if temp_invoice_path is not None:
        temporary_paths.append(temp_invoice_path)

    expected_final_invoice = (
        order.payment_amount is not None
        and order.advance_amount is not None
        and order.payment_amount > order.advance_amount
    )
    if expected_final_invoice and final_invoice_path is None:
        logger.error(
            "_send_post_project_delivery: счёт на остаток недоступен для order=%s",
            order.id,
        )
        return False, temporary_paths
    if final_invoice_path is not None:
        attachment_paths.append(str(final_invoice_path))

    completion_act_path, temp_act_path = _ensure_completion_act_attachment(session, order)
    if temp_act_path is not None:
        temporary_paths.append(temp_act_path)
    if completion_act_path is not None:
        attachment_paths.append(str(completion_act_path))
    else:
        logger.warning(
            "_send_post_project_delivery: акт выполненных работ не создан для order=%s",
            order.id,
        )

    send_fn = send_project_redelivery if is_redelivery else send_project
    success = send_fn(
        session,
        order,
        attachment_paths=attachment_paths,
    )
    return success, temporary_paths


@celery_app.task(
    name="app.services.tasks.send_completed_project",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def send_completed_project(self, order_id: str):
    """Отправка готового проекта клиенту (ADVANCE_PAID → AWAITING_FINAL_PAYMENT).

    Находит сгенерированный PDF проекта в файлах заявки,
    генерирует DOCX сопроводительного письма в РСО,
    отправляет клиенту письмом с вложениями.
    """
    oid = uuid.UUID(order_id)
    logger.info("send_completed_project: order=%s", oid)

    temporary_paths: list[Path] = []

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return
        if order.status != OrderStatus.ADVANCE_PAID:
            logger.warning(
                "send_completed_project: order=%s статус %s, пропускаем",
                oid,
                order.status.value,
            )
            return

        latest_project = _latest_order_file(order, FileCategory.GENERATED_PROJECT)
        latest_project_path = _existing_order_file_path(order, FileCategory.GENERATED_PROJECT)
        if latest_project_path is None:
            logger.warning(
                "send_completed_project: order=%s — актуальный generated_project недоступен "
                "(запись в БД: %s, файл на диске отсутствует или путь неверен)",
                oid,
                latest_project.storage_path if latest_project is not None else "нет",
            )
        elif not order.parsed_params:
            logger.warning(
                "send_completed_project: order=%s — parsed_params пуст, "
                "сопроводительное письмо не создано",
                oid,
            )

        success, temporary_paths = _send_post_project_delivery(
            session,
            order,
            is_redelivery=False,
        )

        if success:
            _transition(session, order, OrderStatus.AWAITING_FINAL_PAYMENT)
            logger.info(
                "Проект отправлен клиенту: order=%s → awaiting_final_payment",
                oid,
            )
        else:
            logger.error("Не удалось отправить проект для order=%s", oid)
            try:
                self.retry()
            except self.MaxRetriesExceededError:
                logger.error("Исчерпаны попытки отправки проекта для order=%s", oid)

    for temp_path in temporary_paths:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError as e:
                logger.warning("Не удалось удалить временный файл %s: %s", temp_path, e)


@celery_app.task(
    name="app.services.tasks.resend_corrected_project",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def resend_corrected_project(self, order_id: str):
    """Повторно отправляет клиенту исправленный проект с тем же счётом на остаток."""
    oid = uuid.UUID(order_id)
    logger.info("resend_corrected_project: order=%s", oid)

    temporary_paths: list[Path] = []

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return
        if order.status != OrderStatus.RSO_REMARKS_RECEIVED:
            logger.warning(
                "resend_corrected_project: order=%s статус %s, пропускаем",
                oid,
                order.status.value,
            )
            return

        latest_remarks = _latest_order_file(order, FileCategory.RSO_REMARKS)
        if latest_remarks is None:
            logger.warning(
                "resend_corrected_project: order=%s без замечаний РСО, пропускаем",
                oid,
            )
            return

        latest_project = _latest_order_file(order, FileCategory.GENERATED_PROJECT)
        latest_project_path = _existing_order_file_path(order, FileCategory.GENERATED_PROJECT)
        if latest_project is None or latest_project_path is None:
            logger.warning(
                "resend_corrected_project: order=%s — актуальный PDF проекта недоступен",
                oid,
            )
            return
        if latest_project.created_at <= latest_remarks.created_at:
            logger.warning(
                "resend_corrected_project: order=%s — новая версия проекта после замечаний ещё не загружена",
                oid,
            )
            return

        success, temporary_paths = _send_post_project_delivery(
            session,
            order,
            is_redelivery=True,
        )
        if success:
            _transition(session, order, OrderStatus.AWAITING_FINAL_PAYMENT)
            logger.info(
                "resend_corrected_project: order=%s → awaiting_final_payment",
                oid,
            )
        else:
            logger.error(
                "resend_corrected_project: не удалось отправить проект для order=%s",
                oid,
            )
            try:
                self.retry()
            except self.MaxRetriesExceededError:
                logger.error(
                    "resend_corrected_project: исчерпаны попытки order=%s",
                    oid,
                )

    for temp_path in temporary_paths:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError as err:
                logger.warning(
                    "Не удалось удалить временный файл %s: %s",
                    temp_path,
                    err,
                )


@celery_app.task(name="app.services.tasks.notify_engineer_rso_scan_received")
def notify_engineer_rso_scan_received(order_id: str):
    """Уведомление инженеру: клиент загрузил скан РСО."""

    from app.services.email_service import send_email

    oid = uuid.UUID(order_id)
    logger.info("notify_engineer_rso_scan_received: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            logger.error("notify_engineer_rso_scan_received: заявка не найдена %s", oid)
            return

        order_id_short = str(order.id)[:8]
        subject = f"Клиент загрузил скан РСО — заявка №{order_id_short}"
        admin_url = f"{settings.app_base_url}/admin?order={order.id}"
        html_body = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;line-height:1.55">
<p>Клиент <strong>{escape(order.client_name)}</strong> загрузил скан письма с входящим номером РСО.</p>
<p><a href="{escape(admin_url)}">Открыть заявку в админке</a></p>
</body></html>"""
        ok = send_email(
            recipient=settings.admin_email,
            subject=subject,
            html_body=html_body,
        )
        if not ok:
            logger.error("notify_engineer_rso_scan_received: не удалось отправить письмо %s", oid)


@celery_app.task(name="app.services.tasks.notify_engineer_rso_remarks_received")
def notify_engineer_rso_remarks_received(order_id: str):
    """Уведомление инженеру: клиент загрузил замечания РСО."""

    from app.services.email_service import send_email

    oid = uuid.UUID(order_id)
    logger.info("notify_engineer_rso_remarks_received: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            logger.error("notify_engineer_rso_remarks_received: заявка не найдена %s", oid)
            return

        order_id_short = str(order.id)[:8]
        admin_url = f"{settings.app_base_url}/admin?order={order.id}"
        subject = f"Клиент загрузил замечания РСО — заявка №{order_id_short}"
        html_body = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;line-height:1.55">
<p>Клиент <strong>{escape(order.client_name)}</strong> загрузил замечания РСО по проекту.</p>
<p><a href="{escape(admin_url)}">Открыть заявку в админке</a></p>
</body></html>"""
        ok = send_email(
            recipient=settings.admin_email,
            subject=subject,
            html_body=html_body,
        )
        if not ok:
            logger.error(
                "notify_engineer_rso_remarks_received: не удалось отправить письмо %s",
                oid,
            )


@celery_app.task(name="app.services.tasks.notify_client_after_rso_scan")
def notify_client_after_rso_scan(order_id: str):
    """Уведомление клиенту после загрузки скана сопроводительного письма в РСО."""
    from app.services.email_service import send_final_payment_request

    oid = uuid.UUID(order_id)
    logger.info("notify_client_after_rso_scan: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            logger.error("notify_client_after_rso_scan: заявка не найдена %s", oid)
            return
        if order.status != OrderStatus.AWAITING_FINAL_PAYMENT:
            logger.info(
                "notify_client_after_rso_scan: пропуск, статус order=%s — %s",
                oid,
                order.status.value,
            )
            return

        if _has_successful_final_payment_reminder(session, oid, "post_rso_scan"):
            logger.info(
                "notify_client_after_rso_scan: письмо уже отправлялось order=%s",
                oid,
            )
            return

        sent = send_final_payment_request(
            session,
            order,
            retry_count=order.retry_count,
            post_rso_scan=True,
            reminder_kind="post_rso_scan",
        )
        if not sent:
            logger.error(
                "notify_client_after_rso_scan: не удалось отправить письмо клиенту order=%s",
                oid,
            )


@celery_app.task(name="app.services.tasks.notify_engineer_signed_contract")
def notify_engineer_signed_contract(order_id: str):
    """Уведомление инженеру: клиент загрузил подписанный договор."""
    from app.services.email_service import send_signed_contract_notification

    oid = uuid.UUID(order_id)
    logger.info("notify_engineer_signed_contract: order=%s", oid)

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            logger.error("notify_engineer_signed_contract: заявка не найдена %s", oid)
            return
        send_signed_contract_notification(session, order)
