"""Сервис отправки email-уведомлений.

Синхронный — вызывается из Celery-задач.
Использует smtplib (SSL/TLS) + Jinja2 для рендеринга шаблонов.
"""

import logging
import smtplib
import ssl
import uuid
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import EmailLog, EmailType, Order
from app.services.param_labels import get_missing_items, get_sample_paths

logger = logging.getLogger(__name__)


# ─── Jinja2 ──────────────────────────────────────────────────────────────────

_jinja_env: Environment | None = None


def _get_jinja() -> Environment:
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=FileSystemLoader(str(settings.templates_dir)),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _jinja_env


# ─── Общие данные для всех шаблонов ─────────────────────────────────────────

_COMMON_CONTEXT = {
    "company_name": "УУТЭ Проектировщик",
    "support_email": settings.smtp_from,
}


def _order_context(order: Order) -> dict:
    """Базовый контекст из заявки."""
    order_id_str = str(order.id)
    return {
        **_COMMON_CONTEXT,
        "order_id": order_id_str,
        "order_id_short": order_id_str[:8],
        "client_name": order.client_name,
        "client_email": order.client_email,
        "object_address": order.object_address,
        "upload_url": f"{settings.app_base_url}/upload/{order.id}",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Рендеринг писем
# ═══════════════════════════════════════════════════════════════════════════════


def render_info_request(order: Order) -> tuple[str, str, list[str]]:
    """Рендерит письмо «Запрос дополнительной информации».

    Returns:
        (subject, html_body, attachment_paths)
    """
    env = _get_jinja()
    template = env.get_template("emails/info_request.html")

    missing = order.missing_params or []
    missing_items = get_missing_items(missing)
    sample_paths = get_sample_paths(missing)

    ctx = {
        **_order_context(order),
        "header_title": "Запрос документов",
        "missing_items": missing_items,
        "has_samples": len(sample_paths) > 0,
    }

    subject = f"Запрос документов для проекта УУТЭ — {order.object_address or 'заявка'}"
    html_body = template.render(ctx)

    # Полные пути к образцам
    full_paths = [
        str(settings.templates_dir / p) for p in sample_paths
        if (settings.templates_dir / p).exists()
    ]

    return subject, html_body, full_paths


def render_reminder(order: Order) -> tuple[str, str, list[str]]:
    """Рендерит письмо-напоминание."""
    env = _get_jinja()
    template = env.get_template("emails/reminder.html")

    missing = order.missing_params or []
    missing_items = get_missing_items(missing)

    ctx = {
        **_order_context(order),
        "header_title": "Напоминание",
        "missing_items": missing_items,
        "retry_count": order.retry_count,
    }

    subject = f"Напоминание: необходимы документы для проекта УУТЭ"
    html_body = template.render(ctx)
    return subject, html_body, []


def render_project_delivery(
    order: Order,
    project_documents: list[str] | None = None,
    attachment_paths: list[str] | None = None,
    download_url: str | None = None,
) -> tuple[str, str, list[str]]:
    """Рендерит письмо «Проект готов»."""
    env = _get_jinja()
    template = env.get_template("emails/project_delivery.html")

    attachments = attachment_paths or []
    docs = project_documents or ["Пояснительная записка", "Чертежи (PDF)"]

    ctx = {
        **_order_context(order),
        "header_title": "Проект готов",
        "project_documents": docs,
        "has_attachments": len(attachments) > 0,
        "download_url": download_url,
    }

    subject = f"Проект УУТЭ готов — {order.object_address or 'заявка'}"
    html_body = template.render(ctx)
    return subject, html_body, attachments


def render_error_notification(
    order: Order,
    error_description: str,
    action_required: str | None = None,
) -> tuple[str, str, list[str]]:
    """Рендерит письмо об ошибке."""
    env = _get_jinja()
    template = env.get_template("emails/error_notification.html")

    ctx = {
        **_order_context(order),
        "header_title": "Требуется внимание",
        "error_description": error_description,
        "action_required": action_required,
    }

    subject = f"Проект УУТЭ: требуется ваше внимание"
    html_body = template.render(ctx)
    return subject, html_body, []


# ═══════════════════════════════════════════════════════════════════════════════
# SMTP-отправка
# ═══════════════════════════════════════════════════════════════════════════════


def _build_message(
    recipient: str,
    subject: str,
    html_body: str,
    attachment_paths: list[str] | None = None,
) -> MIMEMultipart:
    """Собирает MIME-сообщение."""
    msg = MIMEMultipart("mixed")
    msg["From"] = formataddr((settings.smtp_from_name, settings.smtp_from))
    msg["To"] = recipient
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)

    # HTML-тело
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Вложения
    for path_str in (attachment_paths or []):
        path = Path(path_str)
        if not path.exists():
            logger.warning("Вложение не найдено: %s", path)
            continue

        with open(path, "rb") as f:
            part = MIMEApplication(f.read(), Name=path.name)
        part.add_header(
            "Content-Disposition", "attachment", filename=path.name
        )
        msg.attach(part)

    return msg


def send_email(
    recipient: str,
    subject: str,
    html_body: str,
    attachment_paths: list[str] | None = None,
) -> bool:
    """Отправляет email через SMTP.

    Returns:
        True если отправлено успешно, False при ошибке.
    """
    msg = _build_message(recipient, subject, html_body, attachment_paths)

    try:
        if settings.smtp_use_ssl:
            # SSL (порт 465)
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, context=context, timeout=30
            ) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            # STARTTLS (порт 587)
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=30
            ) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)

        logger.info("Email отправлен: %s → %s", subject[:50], recipient)
        return True

    except Exception as e:
        logger.error("Ошибка отправки email на %s: %s", recipient, e, exc_info=True)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Высокоуровневые функции (рендер + отправка + лог в БД)
# ═══════════════════════════════════════════════════════════════════════════════


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


def _log_email(
    session: Session,
    order: Order,
    email_type: EmailType,
    subject: str,
    body: str,
    success: bool,
    error_msg: str | None = None,
) -> EmailLog:
    """Создаёт запись в email_log."""
    log = EmailLog(
        order_id=order.id,
        email_type=email_type,
        recipient=order.client_email,
        subject=subject,
        body_text=body[:5000],  # Обрезаем, чтобы не раздувать БД
        sent_at=datetime.now(timezone.utc) if success else None,
        error_message=error_msg,
    )
    session.add(log)
    session.commit()
    return log


def send_info_request(session: Session, order: Order) -> bool:
    """Отправить клиенту запрос на доп. информацию.

    Рендерит шаблон, отправляет, логирует.
    """
    subject, html_body, attachments = render_info_request(order)

    success = send_email(
        recipient=order.client_email,
        subject=subject,
        html_body=html_body,
        attachment_paths=attachments,
    )

    _log_email(
        session, order, EmailType.INFO_REQUEST,
        subject, html_body, success,
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

    _log_email(
        session, order, EmailType.REMINDER,
        subject, html_body, success,
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

    _log_email(
        session, order, EmailType.PROJECT_DELIVERY,
        subject, html_body, success,
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
    subject, html_body, _ = render_error_notification(
        order, error_description, action_required
    )

    success = send_email(
        recipient=order.client_email,
        subject=subject,
        html_body=html_body,
    )

    _log_email(
        session, order, EmailType.ERROR_NOTIFICATION,
        subject, html_body, success,
        error_msg=None if success else "SMTP delivery failed",
    )
    return success


def send_sample_delivery(recipient_email: str) -> bool:
    """Отправить образец проекта на email."""
    env = _get_jinja()
    template = env.get_template("emails/sample_delivery.html")

    ctx = {
        **_COMMON_CONTEXT,
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


def render_client_documents_received(order: Order) -> tuple[str, str]:
    """Письмо инженеру: клиент завершил загрузку документов."""
    env = _get_jinja()
    template = env.get_template("emails/client_documents_received.html")
    order_id_str = str(order.id)
    ctx = {
        **_order_context(order),
        "header_title": "Документы от клиента",
        "admin_url": f"{settings.app_base_url}/admin?order={order.id}",
        "order_id_short": order_id_str[:8],
    }
    subject = f"Клиент отправил документы — заявка №{order_id_str[:8]}"
    return subject, template.render(ctx)


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
    env = _get_jinja()
    template = env.get_template("emails/new_order_notification.html")

    order_id_str = str(order.id)
    ctx = {
        **_COMMON_CONTEXT,
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
        # Ссылка на HTML-админку, не на JSON API (браузер не шлёт X-Admin-Key).
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
    env = _get_jinja()
    template = env.get_template("emails/partnership_request.html")

    ctx = {
        **_COMMON_CONTEXT,
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
        f"<p><b>Организация:</b> {organization}</p>"
        f"<p><b>ФИО ответственного:</b> {responsible_name}</p>"
        f"<p><b>Телефон:</b> {phone}</p>"
        f"<p><b>Email:</b> {email}</p>"
        "<p>Технические условия приложены к письму.</p>"
        "</body></html>"
    )
    subject = f"Запрос КП — {organization}"

    msg = MIMEMultipart("mixed")
    msg["From"] = formataddr((settings.smtp_from_name, settings.smtp_from))
    msg["To"] = settings.admin_email
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    part = MIMEApplication(tu_bytes, Name=tu_filename)
    part.add_header("Content-Disposition", "attachment", filename=tu_filename)
    msg.attach(part)

    try:
        if settings.smtp_use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, context=context, timeout=30
            ) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=30
            ) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        logger.info("Запрос КП отправлен инженеру: %s", organization)
        return True
    except Exception as e:
        logger.error("Ошибка отправки запроса КП: %s", e, exc_info=True)
        return False


def send_survey_reminder(session: Session, order: Order) -> bool:
    """Отправить клиенту письмо с напоминанием заполнить опросный лист (только для custom-заказов)."""
    env = _get_jinja()
    template = env.get_template("emails/survey_reminder.html")

    order_id_str = str(order.id)
    upload_url = f"{settings.app_base_url}/upload/{order_id_str}"
    ctx = {
        **_COMMON_CONTEXT,
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
