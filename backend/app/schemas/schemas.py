from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.models import EmailType, FileCategory, OrderStatus, OrderType


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
    parsed_params: dict | None
    missing_params: list | None
    survey_data: dict | None
    retry_count: int
    reviewer_comment: str | None
    created_at: datetime
    updated_at: datetime
    files: list["FileResponse"]
    emails: list["EmailLogResponse"]

    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    """Краткая информация о заявке для списка."""

    id: UUID
    status: OrderStatus
    order_type: OrderType
    client_name: str
    client_email: str
    object_address: str | None
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
    missing_params: list[str]
    files_uploaded: list[FileResponse]


class PipelineResponse(BaseModel):
    """Ответ эндпоинтов пайплайна и публичного submit на лендинге."""

    message: str
    order_id: UUID
    task_id: str | None = None
