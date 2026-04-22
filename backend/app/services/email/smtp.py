"""
 * @file: smtp.py
 * @description: Сборка MIME и доставка через SMTP (SSL / STARTTLS).
 * @dependencies: app.core.config.settings
 * @created: 2026-04-22
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def build_mime_message(
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

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    for path_str in attachment_paths or []:
        path = Path(path_str)
        if not path.exists():
            logger.warning("Вложение не найдено: %s", path)
            continue

        with open(path, "rb") as f:
            part = MIMEApplication(f.read(), Name=path.name)
        part.add_header("Content-Disposition", "attachment", filename=path.name)
        msg.attach(part)

    return msg


def send_smtp_message(msg: MIMEMultipart) -> bool:
    """Отправляет уже собранное MIME-сообщение (единая точка SSL/STARTTLS + login)."""
    try:
        if settings.smtp_use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, context=context, timeout=30
            ) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)

        subj = (msg.get("Subject") or "")[:50]
        to_addr = msg.get("To") or ""
        logger.info("Email отправлен: %s → %s", subj, to_addr)
        return True

    except Exception as e:
        to_addr = msg.get("To") or ""
        logger.error("Ошибка отправки email на %s: %s", to_addr, e, exc_info=True)
        return False


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
    msg = build_mime_message(recipient, subject, html_body, attachment_paths)
    return send_smtp_message(msg)
