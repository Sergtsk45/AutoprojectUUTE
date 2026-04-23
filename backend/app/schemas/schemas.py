"""
@file: app/schemas/schemas.py
@description: Pydantic-схемы API — DTO для заявок, файлов, email-логов, публичных
    страниц клиента. Фаза B1.c (2026-04-22): `parsed_params`, `survey_data`,
    `company_requisites` в `OrderResponse`/`UploadPageInfo`/`PaymentPageInfo`
    переведены на строгие Pydantic-модели из `app.schemas.jsonb` — OpenAPI-
    контракт описывает точную структуру JSONB-полей, TS-клиенты (E1) получают
    полноценные типы.
@dependencies: pydantic v2, app.schemas.jsonb.*, app.repositories.order_jsonb.*
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.models import EmailType, FileCategory, OrderStatus, OrderType, PaymentMethod
from app.post_project_state import derive_post_project_flags
from app.repositories.order_jsonb import (
    get_company_requisites,
    get_parsed_params,
    get_survey_data,
)
from app.schemas.jsonb import (
    CompanyRequisites,
    CompanyRequisitesError,
    SurveyData,
    TUParsedData,
)

if TYPE_CHECKING:
    from app.models.models import Order as OrderModel


# Типизированное представление «реквизитов клиента» в публичных DTO:
# либо валидная карточка, либо маркер неудачного парсинга, либо пусто.
CompanyRequisitesResponse = CompanyRequisites | CompanyRequisitesError


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
    """Ответ API — полная информация о заявке.

    JSONB-поля (`parsed_params`, `survey_data`, `company_requisites`) с B1.c
    типизированы строго. Валидация происходит в `build_order_response` через
    accessor'ы `app.repositories.order_jsonb.*` — невалидные исторические
    записи становятся `None` (+ WARNING в лог), а `OrderResponse` не падает.

    Поле `missing_params: list[str] | None` сохранено как plain-строки:
    в БД возможны legacy-коды (`floor_plan`, `connection_scheme` и т. п.),
    которые сервис `fix_legacy_client_document_params` приводит к канонике
    только при открытии страницы загрузки клиентом. Для админки эти коды
    иногда важно видеть «как есть».
    """

    id: UUID
    status: OrderStatus
    order_type: OrderType
    client_name: str
    client_email: str
    client_phone: str | None
    client_organization: str | None
    object_address: str | None
    object_city: str | None
    parsed_params: TUParsedData | None
    missing_params: list[str] | None
    survey_data: SurveyData | None
    retry_count: int
    reviewer_comment: str | None
    payment_method: PaymentMethod | None = None
    payment_amount: int | None = None
    advance_amount: int | None = None
    advance_paid_at: datetime | None = None
    final_paid_at: datetime | None = None
    rso_scan_received_at: datetime | None = None
    company_requisites: CompanyRequisitesResponse | None = None
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
    """Информация для страницы загрузки файлов клиентом.

    JSONB-поля типизированы (B1.c). `company_requisites` — `CompanyRequisites`
    для валидных реквизитов либо `CompanyRequisitesError` для маркера ошибки
    парсинга карточки (фронт `upload.html` этот маркер по нынешнему коду
    не показывает, но контракт совпадает с `PaymentPageInfo`).
    """

    order_id: UUID
    client_name: str
    order_status: str
    order_type: str | None = None
    parsed_params: TUParsedData | None = None
    survey_data: SurveyData | None = None
    contract_number: str | None = None
    payment_amount: int | None = None
    advance_amount: int | None = None
    company_requisites: CompanyRequisitesResponse | None = None
    missing_params: list[str]
    files_uploaded: list[FileResponse]


class PaymentPageInfo(BaseModel):
    """Информация для страницы оплаты клиентом.

    `company_requisites` с B1.c — строгий Union. Фронт `payment.html` по-прежнему
    проверяет `data.company_requisites && data.company_requisites.error` — при
    ошибке парсинга бэкенд отдаёт `CompanyRequisitesError` (`{"error": "..."}`)
    и флоу остаётся прежним.
    """

    order_id: UUID
    client_name: str
    client_email: str
    object_address: str | None
    order_status: str
    order_type: str | None = None
    payment_method: str | None = None
    payment_amount: int | None = None
    advance_amount: int | None = None
    company_requisites: CompanyRequisitesResponse | None = None
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


# ═══════════════════════════════════════════════════════════════════════════════
# BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════


def company_requisites_for_response(
    order: "OrderModel",
) -> CompanyRequisitesResponse | None:
    """Единый хелпер сборки `company_requisites` для публичных DTO.

    - Пустое поле → `None`.
    - Запись-маркер `{"error": "..."}` → `CompanyRequisitesError`
      (фронты `admin.html` / `payment.html` показывают баннер с ошибкой).
    - Нормальные реквизиты → `CompanyRequisites`
      (через accessor `get_company_requisites` — валидирует `extra='ignore'`,
      на грязных данных возвращает `None` + WARNING в лог).
    """
    raw = order.company_requisites
    if not raw:
        return None
    if isinstance(raw, dict) and raw.get("error"):
        return CompanyRequisitesError(error=str(raw["error"]))
    return get_company_requisites(order)


def build_order_response(order: "OrderModel") -> OrderResponse:
    """Собирает `OrderResponse` с флагами одноразовых писем и типизированными JSONB.

    Не использует `OrderResponse.model_validate(order)`, чтобы не зависеть от
    автоматической валидации JSONB-полей на ORM-объекте. Вместо этого JSONB
    читается через accessor'ы (`get_parsed_params`, `get_survey_data`,
    `get_company_requisites`) — они уже логируют WARNING и возвращают `None`
    на невалидных исторических записях, что сохраняет прежнее поведение
    «ответ не падает на грязных данных».
    """
    emails = list(order.emails or [])
    files_orm = list(order.files or [])

    info_request_sent = any(
        e.email_type == EmailType.INFO_REQUEST and e.sent_at is not None for e in emails
    )
    reminder_sent = any(
        e.email_type == EmailType.REMINDER and e.sent_at is not None for e in emails
    )
    earliest_auto: datetime | None = None
    if (
        not info_request_sent
        and order.waiting_client_info_at is not None
        and order.status == OrderStatus.WAITING_CLIENT_INFO
    ):
        earliest_auto = order.waiting_client_info_at + timedelta(hours=24)

    post_project_flags = derive_post_project_flags(
        files_orm,
        order.final_paid_at,
        order.status,
    )

    return OrderResponse(
        id=order.id,
        status=order.status,
        order_type=order.order_type,
        client_name=order.client_name,
        client_email=order.client_email,
        client_phone=order.client_phone,
        client_organization=order.client_organization,
        object_address=order.object_address,
        object_city=order.object_city,
        parsed_params=get_parsed_params(order),
        missing_params=list(order.missing_params) if order.missing_params else None,
        survey_data=get_survey_data(order),
        retry_count=order.retry_count,
        reviewer_comment=order.reviewer_comment,
        payment_method=order.payment_method,
        payment_amount=order.payment_amount,
        advance_amount=order.advance_amount,
        advance_paid_at=order.advance_paid_at,
        final_paid_at=order.final_paid_at,
        rso_scan_received_at=order.rso_scan_received_at,
        company_requisites=company_requisites_for_response(order),
        contract_number=order.contract_number,
        created_at=order.created_at,
        updated_at=order.updated_at,
        files=[FileResponse.model_validate(f) for f in files_orm],
        emails=[EmailLogResponse.model_validate(e) for e in emails],
        info_request_sent=info_request_sent,
        reminder_sent=reminder_sent,
        info_request_earliest_auto_at=earliest_auto,
        **post_project_flags,
    )
