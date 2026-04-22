"""
* @file: service.py
* @description: Высокоуровневый API: рендер + SMTP + лог в БД.
* @dependencies: .smtp, .idempotency, .renderers, app.models, app.core.config
* @created: 2026-04-22
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from html import escape

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import EmailLog, EmailType, Order

from .idempotency import log_email
from .renderers import (
    COMMON_CONTEXT,
    get_jinja,
    render_advance_received,
    render_client_documents_received,
    render_contract_delivery,
    render_error_notification,
    render_final_payment_received,
    render_final_payment_request,
    render_info_request,
    render_project_delivery,
    render_project_ready_payment,
    render_reminder,
    render_signed_contract_notification,
    render_tu_parsed_notification,
)
from .smtp import send_email, send_smtp_message

logger = logging.getLogger(__name__)


def send_info_request(session: Session, order: Order) -> bool:
    """Отправить клиенту запрос на доп. информацию."""
    subject, html_body, attachments = render_info_request(order)

    success = send_email(
        recipient=order.client_email,
        subject=subject,
        html_body=html_body,
        attachment_paths=attachments,
    )

    log_email(
        session,
        order,
        EmailType.INFO_REQUEST,
        subject,
        html_body,
        success,
        error_msg=None if success else "SMTP delivery failed",
    )
    return success


def send_reminder(session: Session, order: Order) -> bool:
    """Отправить напоминание клиенту."""
    subject, html_body, _ = render_reminder(order)

    success = send_email(
        recipient=order.client_email,
        subject=subject,
        html_body=html_body,
    )

    log_email(
        session,
        order,
        EmailType.REMINDER,
        subject,
        html_body,
        success,
        error_msg=None if success else "SMTP delivery failed",
    )
    return success


def send_project_ready_payment(session: Session, order: Order) -> bool:
    """Отправить клиенту письмо «проект готов — оформите оплату»."""
    subject, html_body, attachments = render_project_ready_payment(order)
    success = send_email(
        recipient=order.client_email,
        subject=subject,
        html_body=html_body,
        attachment_paths=attachments,
    )
    log_email(
        session,
        order,
        EmailType.PROJECT_READY_PAYMENT,
        subject,
        html_body,
        success,
        error_msg=None if success else "SMTP delivery failed",
    )
    return success


def send_project(
    session: Session,
    order: Order,
    attachment_paths: list[str] | None = None,
    download_url: str | None = None,
) -> bool:
    """Отправить готовый проект клиенту."""
    subject, html_body, attachments = render_project_delivery(
        order,
        attachment_paths=attachment_paths,
        download_url=download_url,
    )

    success = send_email(
        recipient=order.client_email,
        subject=subject,
        html_body=html_body,
        attachment_paths=attachments,
    )

    log_email(
        session,
        order,
        EmailType.PROJECT_DELIVERY,
        subject,
        html_body,
        success,
        error_msg=None if success else "SMTP delivery failed",
    )
    return success


def send_project_redelivery(
    session: Session,
    order: Order,
    attachment_paths: list[str] | None = None,
    download_url: str | None = None,
) -> bool:
    """Повторно отправить клиенту исправленный проект."""
    subject, html_body, attachments = render_project_delivery(
        order,
        attachment_paths=attachment_paths,
        download_url=download_url,
        is_redelivery=True,
    )
    success = send_email(
        recipient=order.client_email,
        subject=subject,
        html_body=html_body,
        attachment_paths=attachments,
    )
    log_email(
        session,
        order,
        EmailType.PROJECT_DELIVERY,
        subject,
        html_body,
        success,
        error_msg=None if success else "SMTP delivery failed",
    )
    return success


def send_contract_delivery_to_client(
    session: Session,
    order: Order,
    attachment_paths: list[str],
) -> bool:
    """Отправить клиенту договор и счёт (вложения — пути к .docx)."""
    upload_url = f"{settings.app_base_url}/upload/{order.id}"
    subject, html_body, attachments = render_contract_delivery(
        order, attachment_paths, upload_url=upload_url
    )
    success = send_email(
        recipient=order.client_email,
        subject=subject,
        html_body=html_body,
        attachment_paths=attachments,
    )
    log_email(
        session,
        order,
        EmailType.CONTRACT_DELIVERY,
        subject,
        html_body,
        success,
        error_msg=None if success else "SMTP delivery failed",
    )
    return success


def send_signed_contract_notification(session: Session, order: Order) -> bool:
    """Отправить инженеру уведомление о загрузке signed_contract и записать лог."""
    subject, html_body = render_signed_contract_notification(order)
    success = send_email(
        recipient=settings.admin_email,
        subject=subject,
        html_body=html_body,
    )
    log = EmailLog(
        order_id=order.id,
        email_type=EmailType.SIGNED_CONTRACT_NOTIFICATION,
        recipient=settings.admin_email,
        subject=subject,
        body_text=html_body[:5000],
        sent_at=datetime.now(timezone.utc) if success else None,
        error_message=None if success else "SMTP delivery failed",
    )
    session.add(log)
    session.commit()
    return success


def send_advance_received(
    session: Session,
    order: Order,
    attachment_paths: list[str],
    project_documents: list[str] | None = None,
) -> bool:
    """Отправить клиенту письмо «аванс получен» с проектом во вложениях."""
    subject, html_body, attachments = render_advance_received(
        order,
        project_documents=project_documents,
        attachment_paths=attachment_paths,
    )
    success = send_email(
        recipient=order.client_email,
        subject=subject,
        html_body=html_body,
        attachment_paths=attachments,
    )
    log_email(
        session,
        order,
        EmailType.ADVANCE_RECEIVED,
        subject,
        html_body,
        success,
        error_msg=None if success else "SMTP delivery failed",
    )
    return success


def send_final_payment_request(
    session: Session,
    order: Order,
    retry_count: int = 0,
    post_rso_scan: bool = False,
    reminder_kind: str = "default",
) -> bool:
    """Напоминание об остатке оплаты (Celery Beat или вручную)."""
    subject, html_body, attachments = render_final_payment_request(
        order,
        retry_count=retry_count,
        post_rso_scan=post_rso_scan,
        reminder_kind=reminder_kind,
    )
    success = send_email(
        recipient=order.client_email,
        subject=subject,
        html_body=html_body,
        attachment_paths=attachments,
    )
    log_email(
        session,
        order,
        EmailType.FINAL_PAYMENT_REQUEST,
        subject,
        html_body,
        success,
        error_msg=None if success else "SMTP delivery failed",
    )
    return success


def send_final_payment_received(session: Session, order: Order) -> bool:
    """Письмо клиенту после полной оплаты."""
    subject, html_body, attachments = render_final_payment_received(order)
    success = send_email(
        recipient=order.client_email,
        subject=subject,
        html_body=html_body,
        attachment_paths=attachments,
    )
    log_email(
        session,
        order,
        EmailType.FINAL_PAYMENT_RECEIVED,
        subject,
        html_body,
        success,
        error_msg=None if success else "SMTP delivery failed",
    )
    return success


def send_error_notification(
    session: Session,
    order: Order,
    error_description: str,
    action_required: str | None = None,
) -> bool:
    """Уведомить клиента об ошибке."""
    subject, html_body, _ = render_error_notification(order, error_description, action_required)

    success = send_email(
        recipient=order.client_email,
        subject=subject,
        html_body=html_body,
    )

    log_email(
        session,
        order,
        EmailType.ERROR_NOTIFICATION,
        subject,
        html_body,
        success,
        error_msg=None if success else "SMTP delivery failed",
    )
    return success


def send_sample_delivery(recipient_email: str) -> bool:
    """Отправить образец проекта на email."""
    env = get_jinja()
    template = env.get_template("emails/sample_delivery.html")

    ctx = {
        **COMMON_CONTEXT,
        "header_title": "Образец проекта УУТЭ",
        "order_id": None,
        "order_url": f"{settings.app_base_url}/#calculator",
    }

    subject = "Образец проекта узла учёта тепловой энергии"
    html_body = template.render(ctx)

    sample_path = settings.templates_dir / "samples" / "sample_project.pdf"
    attachments = [str(sample_path)] if sample_path.exists() else []

    return send_email(
        recipient=recipient_email,
        subject=subject,
        html_body=html_body,
        attachment_paths=attachments,
    )


def send_tu_parsed_notification(session: Session, order: Order) -> bool:
    """Уведомить инженера после успешного парсинга ТУ."""
    subject, html_body = render_tu_parsed_notification(order)
    success = send_email(
        recipient=settings.admin_email,
        subject=subject,
        html_body=html_body,
    )
    log = EmailLog(
        order_id=order.id,
        email_type=EmailType.TU_PARSED_NOTIFICATION,
        recipient=settings.admin_email,
        subject=subject,
        body_text=html_body[:5000],
        sent_at=datetime.now(timezone.utc) if success else None,
        error_message=None if success else "SMTP delivery failed",
    )
    session.add(log)
    session.commit()
    return success


def send_client_documents_received_notification(session: Session, order: Order) -> bool:
    """Уведомить инженера после «Готово» на странице загрузки клиентом."""
    subject, html_body = render_client_documents_received(order)
    success = send_email(
        recipient=settings.admin_email,
        subject=subject,
        html_body=html_body,
    )
    log = EmailLog(
        order_id=order.id,
        email_type=EmailType.CLIENT_DOCUMENTS_RECEIVED,
        recipient=settings.admin_email,
        subject=subject,
        body_text=html_body[:5000],
        sent_at=datetime.now(timezone.utc) if success else None,
        error_message=None if success else "SMTP delivery failed",
    )
    session.add(log)
    session.commit()
    return success


def send_new_order_notification(
    session: Session,
    order: Order,
    circuits: int | None = None,
    price: int | None = None,
    order_type: str | None = None,
) -> bool:
    """Уведомить инженера о новой заявке."""
    env = get_jinja()
    template = env.get_template("emails/new_order_notification.html")

    order_id_str = str(order.id)
    ctx = {
        **COMMON_CONTEXT,
        "header_title": "Новая заявка",
        "order_id": order_id_str,
        "order_id_short": order_id_str[:8],
        "client_name": order.client_name,
        "client_email": order.client_email,
        "client_phone": order.client_phone,
        "client_organization": order.client_organization,
        "object_address": order.object_address,
        "circuits": circuits,
        "price": f"{price:,}".replace(",", " ") if price else None,
        "order_type_label": "Индивидуальный" if order_type == "custom" else "Экспресс",
        "admin_url": f"{settings.app_base_url}/admin?order={order.id}",
    }

    subject = f"Новая заявка №{order_id_str[:8]} — {order.client_name}"
    html_body = template.render(ctx)

    success = send_email(
        recipient=settings.admin_email,
        subject=subject,
        html_body=html_body,
    )
    log = EmailLog(
        order_id=order.id,
        email_type=EmailType.NEW_ORDER_NOTIFICATION,
        recipient=settings.admin_email,
        subject=subject,
        body_text=html_body[:5000],
        sent_at=datetime.now(timezone.utc) if success else None,
        error_message=None if success else "SMTP delivery failed",
    )
    session.add(log)
    session.commit()
    return success


def send_partnership_request(
    contact_name: str,
    company: str,
    contact_email: str,
    contact_phone: str,
) -> bool:
    """Переслать запрос на партнёрство инженеру."""
    env = get_jinja()
    template = env.get_template("emails/partnership_request.html")

    ctx = {
        **COMMON_CONTEXT,
        "header_title": "Запрос на партнёрство",
        "order_id": None,
        "contact_name": contact_name,
        "company": company,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
    }

    subject = f"Запрос на партнёрство от {company}"
    html_body = template.render(ctx)

    return send_email(
        recipient=settings.admin_email,
        subject=subject,
        html_body=html_body,
    )


def send_kp_request_notification(
    organization: str,
    responsible_name: str,
    phone: str,
    email: str,
    tu_filename: str,
    tu_bytes: bytes,
) -> bool:
    """Переслать запрос КП инженеру с файлом ТУ во вложении."""
    html_body = (
        "<html><body style='font-family:sans-serif'>"
        "<h2 style='color:#263238'>Запрос коммерческого предложения</h2>"
        f"<p><b>Организация:</b> {escape(organization)}</p>"
        f"<p><b>ФИО ответственного:</b> {escape(responsible_name)}</p>"
        f"<p><b>Телефон:</b> {escape(phone)}</p>"
        f"<p><b>Email:</b> {escape(email)}</p>"
        "<p>Технические условия приложены к письму.</p>"
        "</body></html>"
    )
    subject = f"Запрос КП — {organization}"

    msg = MIMEMultipart("mixed")
    msg["From"] = formataddr((settings.smtp_from_name, settings.smtp_from))
    msg["To"] = settings.admin_email
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Reply-To"] = email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    part = MIMEApplication(tu_bytes, Name=tu_filename)
    part.add_header("Content-Disposition", "attachment", filename=tu_filename)
    msg.attach(part)

    success = send_smtp_message(msg)
    if success:
        logger.info("Запрос КП отправлен инженеру: %s", organization)
    return success


def send_survey_reminder(session: Session, order: Order) -> bool:
    """Напоминание заполнить опросный лист (только custom-заказы)."""
    env = get_jinja()
    template = env.get_template("emails/survey_reminder.html")

    order_id_str = str(order.id)
    upload_url = f"{settings.app_base_url}/upload/{order_id_str}"
    ctx = {
        **COMMON_CONTEXT,
        "header_title": "Заполните опросный лист",
        "order_id": order_id_str,
        "order_id_short": order_id_str[:8],
        "client_name": order.client_name,
        "object_address": order.object_address,
        "upload_url": upload_url,
    }

    subject = f"Опросный лист для проекта №{order_id_str[:8]}"
    html_body = template.render(ctx)

    success = send_email(
        recipient=order.client_email,
        subject=subject,
        html_body=html_body,
    )
    log = EmailLog(
        order_id=order.id,
        email_type=EmailType.SURVEY_REMINDER,
        recipient=order.client_email,
        subject=subject,
        body_text=html_body[:5000],
        sent_at=datetime.now(timezone.utc) if success else None,
        error_message=None if success else "SMTP delivery failed",
    )
    session.add(log)
    session.commit()
    return success
