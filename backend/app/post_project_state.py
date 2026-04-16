from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.models import FileCategory, OrderStatus


def _category_value(file_obj: Any) -> str | None:
    category = getattr(file_obj, "category", None)
    if category is None:
        return None
    return getattr(category, "value", category)


def _latest_created_at(files: list[object], category_value: str) -> datetime | None:
    timestamps = [
        created_at
        for file_obj in files
        if _category_value(file_obj) == category_value
        for created_at in [getattr(file_obj, "created_at", None)]
        if created_at is not None
    ]
    return max(timestamps) if timestamps else None


def derive_post_project_flags(
    files: list[object],
    final_paid_at: datetime | None,
    order_status: OrderStatus | str | None,
) -> dict[str, bool]:
    """Вычисляет состояние post-project ветки из статуса и хронологии файлов."""
    categories = {
        category_value
        for file_obj in files
        for category_value in [_category_value(file_obj)]
        if category_value is not None
    }
    has_rso_scan = FileCategory.RSO_SCAN.value in categories
    final_invoice_available = FileCategory.FINAL_INVOICE.value in categories

    latest_remarks_at = _latest_created_at(files, FileCategory.RSO_REMARKS.value)
    latest_project_at = _latest_created_at(files, FileCategory.GENERATED_PROJECT.value)
    status_value = getattr(order_status, "value", order_status)

    remarks_are_open = final_paid_at is None and (
        status_value == OrderStatus.RSO_REMARKS_RECEIVED.value
        or (
            latest_remarks_at is not None
            and (latest_project_at is None or latest_remarks_at >= latest_project_at)
        )
    )
    awaiting_rso_feedback = has_rso_scan and not remarks_are_open and final_paid_at is None
    return {
        "has_rso_scan": has_rso_scan,
        "has_rso_remarks": remarks_are_open,
        "awaiting_rso_feedback": awaiting_rso_feedback,
        "final_invoice_available": final_invoice_available,
    }
