"""Celery tasks package. Registry names stay `app.services.tasks.*` (D1.a)."""

from __future__ import annotations

from app.services.param_labels import compute_client_document_missing  # noqa: F401

from ._common import (  # noqa: F401
    INFO_REQUEST_AUTO_DELAY_SECONDS,
    FINAL_PAYMENT_REMINDER_DELAY_DAYS,
    SyncSession,
    _get_order,
    _normalize_client_requisites,
    _transition,
)
from .client_response import (  # noqa: F401
    notify_engineer_client_documents_received,
    notify_engineer_new_order,
    notify_engineer_tu_parsed,
    process_client_response,
    process_due_info_requests,
    send_info_request_email,
)
from .contract_flow import (  # noqa: F401
    parse_company_card_task,
    process_advance_payment,
    process_card_and_contract,
    process_company_card_and_send_contract,
    process_final_payment,
)
from .post_project_flow import (  # noqa: F401
    notify_client_after_rso_scan,
    notify_engineer_rso_remarks_received,
    notify_engineer_rso_scan_received,
    notify_engineer_signed_contract,
    resend_corrected_project,
    send_completed_project,
)
from .reminders import (  # noqa: F401
    send_final_payment_reminders_after_rso_scan,
    send_reminders,
)
from .tu_parsing import check_data_completeness, start_tu_parsing  # noqa: F401

__all__ = [  # explicit for re-exports / type checkers
    "compute_client_document_missing",
    "INFO_REQUEST_AUTO_DELAY_SECONDS",
    "FINAL_PAYMENT_REMINDER_DELAY_DAYS",
    "SyncSession",
    "_get_order",
    "_normalize_client_requisites",
    "_transition",
    "check_data_completeness",
    "notify_client_after_rso_scan",
    "notify_engineer_client_documents_received",
    "notify_engineer_new_order",
    "notify_engineer_rso_remarks_received",
    "notify_engineer_rso_scan_received",
    "notify_engineer_signed_contract",
    "notify_engineer_tu_parsed",
    "parse_company_card_task",
    "process_advance_payment",
    "process_card_and_contract",
    "process_client_response",
    "process_company_card_and_send_contract",
    "process_due_info_requests",
    "process_final_payment",
    "resend_corrected_project",
    "send_completed_project",
    "send_info_request_email",
    "send_reminders",
    "send_final_payment_reminders_after_rso_scan",
    "start_tu_parsing",
]
