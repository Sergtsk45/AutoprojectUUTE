"""
* @file: __init__.py
* @description: Пакет email: SMTP, рендеры, идемпотентность, высокоуровневый API.
* @dependencies: .smtp, .idempotency, .renderers, .service
* @created: 2026-04-22
"""

from __future__ import annotations

from .idempotency import has_successful_email
from .manual_send import ManualSendError, manual_send_email_sync
from .renderers import (
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
from .service import (
    send_advance_received,
    send_client_documents_received_notification,
    send_contract_delivery_to_client,
    send_error_notification,
    send_final_payment_received,
    send_final_payment_request,
    send_info_request,
    send_kp_request_notification,
    send_new_order_notification,
    send_partnership_request,
    send_project,
    send_project_redelivery,
    send_project_ready_payment,
    send_reminder,
    send_sample_delivery,
    send_signed_contract_notification,
    send_survey_reminder,
    send_tu_parsed_notification,
)
from .smtp import send_email

__all__ = [
    "has_successful_email",
    "ManualSendError",
    "manual_send_email_sync",
    "send_email",
    "render_info_request",
    "render_reminder",
    "render_project_delivery",
    "render_project_ready_payment",
    "render_contract_delivery",
    "render_advance_received",
    "render_final_payment_request",
    "render_final_payment_received",
    "render_error_notification",
    "render_signed_contract_notification",
    "render_tu_parsed_notification",
    "render_client_documents_received",
    "send_info_request",
    "send_reminder",
    "send_project_ready_payment",
    "send_project",
    "send_project_redelivery",
    "send_contract_delivery_to_client",
    "send_signed_contract_notification",
    "send_advance_received",
    "send_final_payment_request",
    "send_final_payment_received",
    "send_error_notification",
    "send_sample_delivery",
    "send_tu_parsed_notification",
    "send_client_documents_received_notification",
    "send_new_order_notification",
    "send_partnership_request",
    "send_kp_request_notification",
    "send_survey_reminder",
]
