from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.models import EmailType, FileCategory, OrderStatus, OrderType, PaymentMethod
from app.post_project_state import derive_post_project_flags

if TYPE_CHECKING:
    from app.models.models import Order as OrderModel


# ═══════════════════════════════════════════════════════════════════════════════
# ORDER
# ═══════════════════════════════════════════════════════════════════════════════


class OrderCreate(BaseModel):
    """Создание заявки — данные из формы на лендинге."""

    client_name: str = Field(..., min_length=2, max_length=255, examples=["Иванов И.И."])
    client_email: EmailStr = Field(..., examples=["ivanov@example.ru"])
    client_phone: str | None = Field(None, max_length=50, examples=["+7 999 123-45-67"])
    client_organization: str | None = Field(None, max_length=255, examples=["ООО Теплосеть"])
    object_address: str | None = Field(None, examples=["г. Москва, ул. Строителей, д. 5"])
    object_city: str | None = Field(None, max_length=255, examples=["Москва"])
    order_type: str | None = Field(None)


class OrderStatusUpdate(BaseModel):
    """Ручная смена статуса (для админки / этапа review)."""

    status: OrderStatus
    reviewer_comment: str | None = None


class OrderResponse(BaseModel):
    """Ответ API — полная информация о заявке."""

    id: UUID
    status: OrderStatus
    order_type: OrderType
    client_name: str
    client_email: str
    client_phone: str | None
    client_organization: str | None
    object_address: str | None
    object_city: str | None
    parsed_params: dict | None
    missing_params: list | None
    survey_data: dict | None
    retry_count: int
    reviewer_comment: str | None
    payment_method: PaymentMethod | None = None
    payment_amount: int | None = None
    advance_amount: int | None = None
    advance_paid_at: datetime | None = None
    final_paid_at: datetime | None = None
    rso_scan_received_at: datetime | None = None
    company_requisites: dict | None = None
    contract_number: str | None = None
    created_at: datetime
    updated_at: datetime
    files: list["FileResponse"]
    emails: list["EmailLogResponse"]
    has_rso_scan: bool = False
    has_rso_remarks: bool = False
    awaiting_rso_feedback: bool = False
    final_invoice_available: bool = False
    info_request_sent: bool = False
    reminder_sent: bool = False
    #: Не ранее этого момента (UTC) уйдёт авто-запрос документов, если инженер не отправил раньше.
    info_request_earliest_auto_at: datetime | None = None

    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    """Краткая информация о заявке для списка."""

    id: UUID
    status: OrderStatus
    order_type: OrderType
    client_name: str
    client_email: str
    object_address: str | None
    object_city: str | None
    payment_method: PaymentMethod | None = None
    payment_amount: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
# FILE
# ═══════════════════════════════════════════════════════════════════════════════


class FileResponse(BaseModel):
    """Информация о загруженном файле."""

    id: UUID
    category: FileCategory
    original_filename: str
    content_type: str | None
    file_size: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL LOG
# ═══════════════════════════════════════════════════════════════════════════════


class EmailLogResponse(BaseModel):
    """Лог отправленного письма."""

    id: UUID
    email_type: EmailType
    recipient: str
    subject: str
    sent_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
# UPLOAD PAGE (клиентская страница загрузки)
# ═══════════════════════════════════════════════════════════════════════════════


class UploadPageInfo(BaseModel):
    """Информация для страницы загрузки файлов клиентом."""

    order_id: UUID
    client_name: str
    order_status: str
    order_type: str | None = None
    parsed_params: dict | None = None
    survey_data: dict | None = None
    contract_number: str | None = None
    payment_amount: int | None = None
    advance_amount: int | None = None
    company_requisites: dict | None = None
    missing_params: list[str]
    files_uploaded: list[FileResponse]


class PaymentPageInfo(BaseModel):
    """Информация для страницы оплаты клиентом."""

    order_id: UUID
    client_name: str
    client_email: str
    object_address: str | None
    order_status: str
    order_type: str | None = None
    payment_method: str | None = None
    payment_amount: int | None = None
    advance_amount: int | None = None
    company_requisites: dict | None = None
    payment_requisites: dict | None = None
    contract_number: str | None = None
    has_rso_scan: bool = False
    has_rso_remarks: bool = False
    awaiting_rso_feedback: bool = False
    final_invoice_available: bool = False
    rso_scan_received_at: datetime | None = None
    files_uploaded: list[FileResponse]


class PipelineResponse(BaseModel):
    """Ответ эндпоинтов пайплайна и публичного submit на лендинге."""

    message: str
    order_id: UUID
    task_id: str | None = None


def build_order_response(order: "OrderModel") -> OrderResponse:
    """Собирает OrderResponse с флагами одноразовых писем (по успешным записям в логе)."""
    emails = order.emails or []
    info_request_sent = any(
        e.email_type == EmailType.INFO_REQUEST and e.sent_at is not None
        for e in emails
    )
    reminder_sent = any(
        e.email_type == EmailType.REMINDER and e.sent_at is not None
        for e in emails
    )
    earliest_auto: datetime | None = None
    if (
        not info_request_sent
        and order.waiting_client_info_at is not None
        and order.status == OrderStatus.WAITING_CLIENT_INFO
    ):
        earliest_auto = order.waiting_client_info_at + timedelta(hours=24)

    base = OrderResponse.model_validate(order)
    post_project_flags = derive_post_project_flags(
        order.files or [],
        order.final_paid_at,
        order.status,
    )
    return base.model_copy(
        update={
            **post_project_flags,
            "info_request_sent": info_request_sent,
            "reminder_sent": reminder_sent,
            "info_request_earliest_auto_at": earliest_auto,
        }
    )


