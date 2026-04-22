#!/usr/bin/env python3
"""One-off: split backend/app/services/tasks.py into package tasks/. Run from repo root:
   python3 scripts/split_tasks_d1b.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "backend" / "app" / "services" / "tasks.py"
PKG = ROOT / "backend" / "app" / "services" / "tasks"


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Missing {SRC}")
    lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)

    def T(a: int, b: int) -> str:
        """1-based inclusive line range [a, b] (оба конца входят). Реализация: `lines[a-1:b]`
        в Python, где второй индекс — exclusive, поэтому b = номер **последней** строки
        (например, закрывающая `)` у `logger.info` на стр. 471 — используй b=471, не 470)."""
        return "".join(lines[a - 1 : b])

    PKG.mkdir(parents=True, exist_ok=True)

    # --- _common.py
    common = '"""Common helpers: sync session, requisites, file helpers (D1.b package split)."""\n\n'
    common += T(14, 152) + T(1318, 1343) + T(153, 300)
    (PKG / "_common.py").write_text(common, encoding="utf-8")

    # --- tu_parsing
    tu = T(307, 471)  # inclusive end (закрывающая скобка last logger)
    tu = tu.replace(
        "        send_info_request_email.apply_async(",
        "        client_response.send_info_request_email.apply_async(",
    )
    tu = tu.replace(
        "notify_engineer_tu_parsed.delay(",
        "client_response.notify_engineer_tu_parsed.delay(",
    )
    (PKG / "tu_parsing.py").write_text(
        '"""Парсинг ТУ, check_data (D1.b)."""\n\n'
        "from __future__ import annotations\n\n"
        "import logging\nimport uuid\n\n"
        "from sqlalchemy import select\nfrom sqlalchemy.orm import selectinload\n\n"
        "from app.core.celery_app import celery_app\n"
        "from app.core.config import settings\n"
        "from app.models.models import FileCategory, Order, OrderStatus\n"
        "from app.services.param_labels import compute_client_document_missing\n\n"
        "from . import client_response\n"
        "from ._common import (\n"
        "    INFO_REQUEST_AUTO_DELAY_SECONDS,\n"
        "    SyncSession,\n"
        "    _get_order,\n"
        "    _transition,\n"
        ")\n\n"
        f"logger = logging.getLogger(__name__)\n\n" + tu,
        encoding="utf-8",
    )

    # --- client_response (process_client must lazy-defer contract_flow to avoid import cycle)
    cr = T(474, 678)
    cr = cr.replace(
        "    process_card_and_contract.delay(order_id)\n",
        "    from . import contract_flow\n\n"
        "    contract_flow.process_card_and_contract.delay(order_id)\n",
    )
    (PKG / "client_response.py").write_text(
        '"""Info_request, process_client, beat, engineer notifications (D1.b)."""\n\n'
        "from __future__ import annotations\n\n"
        "import logging\nimport uuid\n\n"
        "from sqlalchemy import select\nfrom sqlalchemy.orm import selectinload\n\n"
        "from app.core.celery_app import celery_app\n"
        "from app.core.config import settings\n"
        "from app.models.models import EmailType, FileCategory, Order, OrderStatus\n"
        "from app.services.param_labels import compute_client_document_missing\n\n"
        "from ._common import SyncSession, _get_order, _transition\n\n"
        f"logger = logging.getLogger(__name__)\n\n" + cr,
        encoding="utf-8",
    )

    # --- contract_flow (no _send_post / send_completed / resend)
    cflow = T(681, 914) + T(1043, 1168) + T(1254, 1316) + T(1346, 1530)
    cflow = cflow.replace(
        "            notify_engineer_client_documents_received.delay(order_id)\n",
        "            client_response.notify_engineer_client_documents_received.delay(order_id)\n",
    )
    (PKG / "contract_flow.py").write_text(
        '"""Contract, advance, pay, company card (payment) (D1.b)."""\n\n'
        "from __future__ import annotations\n\n"
        "import logging\nimport shutil\nimport uuid\nfrom pathlib import Path\n\n"
        "from app.core.celery_app import celery_app\n"
        "from app.core.config import settings\n"
        "from app.repositories.order_jsonb import (\n"
        "    get_company_requisites_dict,\n"
        "    get_parsed_params,\n"
        "    set_company_requisites,\n"
        ")\n"
        "from app.models.models import FileCategory, Order, OrderFile, OrderStatus, PaymentMethod\n\n"
        "from . import client_response\n"
        "from ._common import (\n"
        "    SyncSession,\n"
        "    _existing_order_file_path,\n"
        "    _get_order,\n"
        "    _latest_order_file,\n"
        "    _normalize_client_requisites,\n"
        "    _resolve_initial_payment_amount,\n"
        "    _transition,\n"
        ")\n\n"
        f"logger = logging.getLogger(__name__)\n\n" + cflow,
        encoding="utf-8",
    )

    # --- post_project_flow
    post = T(916, 1035) + T(1170, 1252) + T(1533, 1657)
    (PKG / "post_project_flow.py").write_text(
        '"""Post-project delivery, RSO notifications (D1.b)."""\n\n'
        "from __future__ import annotations\n\n"
        "import logging\nimport uuid\nfrom html import escape\nfrom pathlib import Path\n\n"
        "from sqlalchemy import select\nfrom sqlalchemy.orm import Session, selectinload\n\n"
        "from app.core.celery_app import celery_app\n"
        "from app.core.config import settings\n"
        "from app.models.models import FileCategory, Order, OrderStatus, EmailType\n\n"
        "from ._common import (\n"
        "    SyncSession,\n"
        "    _collect_project_attachments,\n"
        "    _ensure_final_invoice_attachment,\n"
        "    _existing_order_file_path,\n"
        "    _get_order,\n"
        "    _has_successful_final_payment_reminder,\n"
        "    _latest_order_file,\n"
        "    _transition,\n"
        ")\n\n"
        f"logger = logging.getLogger(__name__)\n\n" + post,
        encoding="utf-8",
    )

    # --- reminders: original lines keep inner email_service imports; need celery + _common const
    (PKG / "reminders.py").write_text(
        '"""Celery Beat periodic reminders (D1.b)."""\n\n'
        "from __future__ import annotations\n\n"
        "import logging\n\n"
        "from sqlalchemy import select\n"
        "from sqlalchemy.orm import selectinload\n\n"
        "from app.core.celery_app import celery_app\n"
        "from app.core.config import settings\n"
        "from app.models.models import EmailType, Order, OrderStatus\n\n"
        "from ._common import (\n"
        "    FINAL_PAYMENT_REMINDER_DELAY_DAYS,\n"
        "    SyncSession,\n"
        "    _has_successful_final_payment_reminder,\n"
        ")\n\n"
        f"logger = logging.getLogger(__name__)\n\n" + T(1665, 1777),
        encoding="utf-8",
    )

    (PKG / "__init__.py").write_text(
        '"""Celery tasks package. Registry names stay `app.services.tasks.*` (D1.a)."""\n\n'
        "from __future__ import annotations\n\n"
        "from ._common import (  # noqa: F401\n"
        "    INFO_REQUEST_AUTO_DELAY_SECONDS,\n"
        "    FINAL_PAYMENT_REMINDER_DELAY_DAYS,\n"
        "    SyncSession,\n"
        "    _get_order,\n"
        "    _normalize_client_requisites,\n"
        "    _transition,\n"
        ")\n"
        "from .client_response import (  # noqa: F401\n"
        "    notify_engineer_client_documents_received,\n"
        "    notify_engineer_tu_parsed,\n"
        "    process_client_response,\n"
        "    process_due_info_requests,\n"
        "    send_info_request_email,\n"
        ")\n"
        "from .contract_flow import (  # noqa: F401\n"
        "    fill_excel,\n"
        "    generate_project,\n"
        "    initiate_payment_flow,\n"
        "    parse_company_card_task,\n"
        "    process_advance_payment,\n"
        "    process_card_and_contract,\n"
        "    process_company_card_and_send_contract,\n"
        "    process_final_payment,\n"
        ")\n"
        "from .post_project_flow import (  # noqa: F401\n"
        "    notify_client_after_rso_scan,\n"
        "    notify_engineer_rso_remarks_received,\n"
        "    notify_engineer_rso_scan_received,\n"
        "    notify_engineer_signed_contract,\n"
        "    resend_corrected_project,\n"
        "    send_completed_project,\n"
        ")\n"
        "from .reminders import (  # noqa: F401\n"
        "    send_final_payment_reminders_after_rso_scan,\n"
        "    send_reminders,\n"
        ")\n"
        "from .tu_parsing import check_data_completeness, start_tu_parsing  # noqa: F401\n\n"
        "__all__ = [  # explicit for re-exports / type checkers\n"
        "    'INFO_REQUEST_AUTO_DELAY_SECONDS',\n"
        "    'FINAL_PAYMENT_REMINDER_DELAY_DAYS',\n"
        "    'SyncSession',\n"
        "    '_get_order',\n"
        "    '_normalize_client_requisites',\n"
        "    '_transition',\n"
        "    'check_data_completeness',\n"
        "    'fill_excel',\n"
        "    'generate_project',\n"
        "    'initiate_payment_flow',\n"
        "    'notify_client_after_rso_scan',\n"
        "    'notify_engineer_client_documents_received',\n"
        "    'notify_engineer_rso_remarks_received',\n"
        "    'notify_engineer_rso_scan_received',\n"
        "    'notify_engineer_signed_contract',\n"
        "    'notify_engineer_tu_parsed',\n"
        "    'parse_company_card_task',\n"
        "    'process_advance_payment',\n"
        "    'process_card_and_contract',\n"
        "    'process_client_response',\n"
        "    'process_company_card_and_send_contract',\n"
        "    'process_due_info_requests',\n"
        "    'process_final_payment',\n"
        "    'resend_corrected_project',\n"
        "    'send_completed_project',\n"
        "    'send_info_request_email',\n"
        "    'send_reminders',\n"
        "    'send_final_payment_reminders_after_rso_scan',\n"
        "    'start_tu_parsing',\n"
        "]\n",
        encoding="utf-8",
    )

    # remove monolith (caller backs up in git)
    # SRC.unlink()
    print("Generated package under", PKG)
    print("Review then: rm", SRC, "  # after ruff/mypy/pytest pass")


if __name__ == "__main__":
    main()
