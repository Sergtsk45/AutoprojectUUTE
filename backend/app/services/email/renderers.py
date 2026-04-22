"""
 * @file: renderers.py
 * @description: Jinja2-рендеринг HTML-писем и контекстов для шаблонов.
 * @dependencies: app.core.config, app.models.Order, app.services.param_labels
 * @created: 2026-04-22
"""

from __future__ import annotations

from html import escape

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.models.models import Order
from app.services.param_labels import get_missing_items, get_sample_paths

_jinja_env: Environment | None = None


def get_jinja() -> Environment:
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=FileSystemLoader(str(settings.templates_dir)),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _jinja_env


COMMON_CONTEXT = {
    "company_name": "УУТЭ Проектировщик",
    "support_email": settings.smtp_from,
}


def _order_context(order: Order) -> dict:
    """Базовый контекст из заявки."""
    order_id_str = str(order.id)
    return {
        **COMMON_CONTEXT,
        "order_id": order_id_str,
        "order_id_short": order_id_str[:8],
        "client_name": order.client_name,
        "client_email": order.client_email,
        "object_address": order.object_address,
        "upload_url": f"{settings.app_base_url}/upload/{order.id}",
    }


def _format_rub(amount: int | None) -> str:
    if amount is None:
        return "—"
    return f"{amount:,}".replace(",", " ")


def _final_amount_rub(order: Order) -> int | None:
    if order.payment_amount is None or order.advance_amount is None:
        return None
    return order.payment_amount - order.advance_amount


def _contract_number_display(order: Order) -> str:
    oid = str(order.id)
    return (order.contract_number or oid[:8]).strip()


def _executor_bank_context() -> dict:
    return {
        "company_full_name": settings.company_full_name,
        "company_inn": settings.company_inn or "—",
        "company_settlement_account": settings.company_settlement_account or "—",
        "company_bank_name": settings.company_bank_name or "—",
        "company_bik": settings.company_bik or "—",
        "company_corr_account": settings.company_corr_account or "—",
    }


def render_info_request(order: Order) -> tuple[str, str, list[str]]:
    """Рендерит письмо «Запрос дополнительной информации»."""
    env = get_jinja()
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

    full_paths = [
        str(settings.templates_dir / p)
        for p in sample_paths
        if (settings.templates_dir / p).exists()
    ]

    return subject, html_body, full_paths


def render_reminder(order: Order) -> tuple[str, str, list[str]]:
    """Рендерит письмо-напоминание."""
    env = get_jinja()
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
    is_redelivery: bool = False,
) -> tuple[str, str, list[str]]:
    """Рендерит письмо «Проект готов»."""
    env = get_jinja()
    template = env.get_template("emails/project_delivery.html")

    attachments = attachment_paths or []
    docs = project_documents or ["Пояснительная записка", "Чертежи (PDF)"]

    ctx = {
        **_order_context(order),
        "header_title": "Исправленный проект готов" if is_redelivery else "Проект готов",
        "project_documents": docs,
        "has_attachments": len(attachments) > 0,
        "download_url": download_url,
        "payment_url": f"{settings.app_base_url}/payment/{order.id}",
        "is_redelivery": is_redelivery,
    }

    if is_redelivery:
        subject = f"Исправленный проект УУТЭ — {order.object_address or 'заявка'}"
    else:
        subject = f"Проект УУТЭ готов — {order.object_address or 'заявка'}"
    html_body = template.render(ctx)
    return subject, html_body, attachments


def render_project_ready_payment(order: Order) -> tuple[str, str, list[str]]:
    """Письмо клиенту: проект готов, переход к оформлению оплаты."""
    env = get_jinja()
    template = env.get_template("emails/project_ready_payment.html")
    ctx = {
        **_order_context(order),
        "header_title": "Проект готов",
        "payment_url": f"{settings.app_base_url}/payment/{order.id}",
        "payment_amount_formatted": _format_rub(order.payment_amount),
        "advance_amount_formatted": _format_rub(order.advance_amount),
        "final_amount_formatted": _format_rub(_final_amount_rub(order)),
    }
    subject = f"Проект УУТЭ готов — оформление оплаты — {order.object_address or 'заявка'}"
    return subject, template.render(ctx), []


def render_contract_delivery(
    order: Order,
    attachment_paths: list[str],
    upload_url: str,
) -> tuple[str, str, list[str]]:
    """Письмо клиенту: договор и счёт на аванс (вложения — пути к файлам)."""
    env = get_jinja()
    template = env.get_template("emails/contract_delivery.html")
    attachments = list(attachment_paths)
    cn = _contract_number_display(order)
    ctx = {
        **_order_context(order),
        **_executor_bank_context(),
        "header_title": "Договор и счёт на аванс",
        "upload_url": upload_url,
        "contract_number": cn,
        "advance_amount_formatted": _format_rub(order.advance_amount),
        "has_attachments": len(attachments) > 0,
    }
    subject = f"Договор №{cn} и счёт на оплату — УУТЭ"
    return subject, template.render(ctx), attachments


def render_advance_received(
    order: Order,
    project_documents: list[str] | None = None,
    attachment_paths: list[str] | None = None,
) -> tuple[str, str, list[str]]:
    """Письмо клиенту: аванс получен, проект во вложениях."""
    env = get_jinja()
    template = env.get_template("emails/advance_received.html")
    attachments = list(attachment_paths or [])
    docs = project_documents or [
        "Пояснительная записка",
        "Чертежи (PDF)",
        "Сопроводительное письмо в РСО",
    ]
    cn = _contract_number_display(order)
    ctx = {
        **_order_context(order),
        "header_title": "Аванс получен",
        "payment_url": f"{settings.app_base_url}/payment/{order.id}",
        "contract_number": cn,
        "advance_amount_formatted": _format_rub(order.advance_amount),
        "final_amount_formatted": _format_rub(_final_amount_rub(order)),
        "project_documents": docs,
        "has_attachments": len(attachments) > 0,
    }
    subject = f"Аванс получен — проект УУТЭ — {order.object_address or 'заявка'}"
    return subject, template.render(ctx), attachments


def render_final_payment_request(
    order: Order,
    retry_count: int = 0,
    post_rso_scan: bool = False,
    reminder_kind: str = "default",
) -> tuple[str, str, list[str]]:
    """Напоминание клиенту об остатке оплаты / скане РСО."""
    if post_rso_scan and reminder_kind == "default":
        reminder_kind = "post_rso_scan"

    env = get_jinja()
    template = env.get_template("emails/final_payment_request.html")
    cn = _contract_number_display(order)
    ctx = {
        **_order_context(order),
        "header_title": "Дальнейшие шаги" if post_rso_scan else "Напоминание об оплате",
        "payment_url": f"{settings.app_base_url}/payment/{order.id}",
        "contract_number": cn,
        "final_amount_formatted": _format_rub(_final_amount_rub(order)),
        "retry_count": retry_count,
        "post_rso_scan": post_rso_scan,
        "reminder_kind": reminder_kind,
    }
    if post_rso_scan:
        subject = f"Дальнейшие шаги по проекту УУТЭ — договор №{cn}"
    else:
        subject = f"Напоминание: остаток оплаты — договор №{cn}"
    return subject, template.render(ctx), []


def render_final_payment_received(order: Order) -> tuple[str, str, list[str]]:
    """Письмо клиенту: оплата завершена."""
    env = get_jinja()
    template = env.get_template("emails/final_payment_received.html")
    cn = _contract_number_display(order)
    base = settings.app_base_url.rstrip("/")
    ctx = {
        **_order_context(order),
        "header_title": "Оплата завершена",
        "contract_number": cn,
        "payment_amount_formatted": _format_rub(order.payment_amount),
        "site_url": f"{base}/",
    }
    subject = f"Оплата завершена — договор №{cn} — УУТЭ"
    return subject, template.render(ctx), []


def render_error_notification(
    order: Order,
    error_description: str,
    action_required: str | None = None,
) -> tuple[str, str, list[str]]:
    """Рендерит письмо об ошибке."""
    env = get_jinja()
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


def render_signed_contract_notification(order: Order) -> tuple[str, str]:
    """Письмо инженеру: клиент загрузил подписанный договор."""
    order_id_str = str(order.id)
    admin_url = f"{settings.app_base_url}/admin?order={order.id}"
    subject = f"Клиент загрузил подписанный договор — заявка №{order_id_str[:8]}"
    html_body = (
        "<!DOCTYPE html>"
        "<html><body style='font-family:sans-serif;line-height:1.55'>"
        f"<p>Клиент <strong>{escape(order.client_name)}</strong> загрузил подписанный договор.</p>"
        f"<p>Заявка: <strong>№{order_id_str[:8]}</strong></p>"
        f"<p><a href='{escape(admin_url)}'>Открыть заявку в админке</a></p>"
        "</body></html>"
    )
    return subject, html_body


def render_tu_parsed_notification(order: Order) -> tuple[str, str]:
    """Письмо инженеру: клиент загрузил ТУ, парсинг завершён."""
    env = get_jinja()
    template = env.get_template("emails/tu_parsed_notification.html")
    order_id_str = str(order.id)
    ctx = {
        **_order_context(order),
        "header_title": "ТУ загружено и распарсено",
        "admin_url": f"{settings.app_base_url}/admin?order={order.id}",
        "order_id_short": order_id_str[:8],
        "status_label": "Ожидаем документы от клиента",
        "missing_items": get_missing_items(order.missing_params or []),
    }
    subject = f"Клиент загрузил ТУ — заявка №{order_id_str[:8]}"
    return subject, template.render(ctx)


def render_client_documents_received(order: Order) -> tuple[str, str]:
    """Письмо инженеру: клиент завершил загрузку документов."""
    env = get_jinja()
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
