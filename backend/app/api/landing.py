"""API-эндпоинты для форм лендинга.

Публичные (без авторизации) — вызываются фронтендом.
"""

import uuid

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import FileCategory, OrderStatus, OrderType
from app.services.param_labels import CLIENT_DOCUMENT_PARAM_CODES
from app.services import OrderService
from app.services.email_service import send_kp_request_notification
from app.services.tasks import start_tu_parsing
from app.schemas import FileResponse, OrderCreate, PipelineResponse, UploadPageInfo

router = APIRouter(prefix="/landing", tags=["landing"])

# Статусы, в которых клиент может сохранить опрос по публичной ссылке (UUID).
_SURVEY_SAVE_ALLOWED: frozenset[OrderStatus] = frozenset(
    {
        OrderStatus.TU_PARSED,
        OrderStatus.WAITING_CLIENT_INFO,
        OrderStatus.CLIENT_INFO_RECEIVED,
        OrderStatus.DATA_COMPLETE,
        OrderStatus.GENERATING_PROJECT,
    }
)

_MAX_TU_SIZE = 20 * 1024 * 1024  # 20 МБ — максимальный размер файла ТУ


# ── Schemas ──────────────────────────────────────────────────────────────────


class SampleRequest(BaseModel):
    email: EmailStr


class OrderRequest(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=255)
    client_email: EmailStr
    client_phone: str | None = Field(None, max_length=50)
    client_organization: str | None = Field(None, max_length=255)
    object_address: str | None = None
    object_city: str = Field(..., min_length=2, max_length=255)
    circuits: int | None = Field(None, ge=1, le=10)
    price: int | None = None
    order_type: str = Field("express", pattern="^(express|custom)$")


class OrderCreatedResponse(BaseModel):
    order_id: str
    upload_url: str
    message: str


class PartnershipRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    company: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=5, max_length=50)


# Справочная схема для документации — в эндпоинте используются Form() параметры напрямую
class KpRequest(BaseModel):
    organization: str = Field(..., min_length=2, max_length=255)
    responsible_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=5, max_length=50)
    email: EmailStr


class SimpleResponse(BaseModel):
    success: bool
    message: str


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/sample-request", response_model=SimpleResponse)
async def request_sample(data: SampleRequest):
    """Сценарий A: Клиент запросил образец проекта.

    Отправляет PDF-образец на email (если файл есть),
    или просто подтверждение.
    """
    from app.services.email_service import send_sample_delivery

    send_sample_delivery(data.email)

    return SimpleResponse(
        success=True,  # Всегда true для UX — даже если SMTP упал, не пугаем клиента
        message="Образец отправлен на вашу почту",
    )


@router.post("/order", response_model=OrderCreatedResponse, status_code=201)
async def create_order_from_landing(
    data: OrderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Сценарий B: Клиент заказывает проект.

    Создаёт заявку в БД, уведомляет инженера, возвращает ссылку на upload-страницу.
    """
    from app.core.config import settings
    from app.services.email_service import send_new_order_notification
    from app.services.tasks import SyncSession, _get_order

    svc = OrderService(db)
    order_data = OrderCreate(
        client_name=data.client_name,
        client_email=data.client_email,
        client_phone=data.client_phone,
        client_organization=data.client_organization,
        object_address=data.object_address,
        object_city=data.object_city,
        order_type=data.order_type,
    )
    order = await svc.create_order(order_data)

    # Уведомление инженеру + письмо клиенту для custom (синхронно через отдельную сессию)
    try:
        with SyncSession() as sync_session:
            sync_order = _get_order(sync_session, order.id)
            if sync_order:
                send_new_order_notification(
                    sync_session, sync_order,
                    circuits=data.circuits,
                    price=data.price,
                    order_type=data.order_type,
                )
    except Exception:
        pass  # Не ломаем создание заявки из-за проблем с email

    upload_url = f"{settings.app_base_url}/upload/{order.id}"

    return OrderCreatedResponse(
        order_id=str(order.id),
        upload_url=upload_url,
        message="Заявка создана",
    )


@router.post("/partnership", response_model=SimpleResponse)
async def partnership_request(data: PartnershipRequest):
    """Сценарий C: Запрос на партнёрство.

    Пересылает данные на почту инженера.
    """
    from app.services.email_service import send_partnership_request

    send_partnership_request(
        contact_name=data.name,
        company=data.company,
        contact_email=data.email,
        contact_phone=data.phone,
    )

    return SimpleResponse(
        success=True,
        message="Заявка на партнёрство отправлена",
    )


@router.post("/kp-request", response_model=SimpleResponse)
async def kp_request(
    organization: str = Form(..., min_length=2, max_length=255),
    responsible_name: str = Form(..., min_length=2, max_length=255),
    phone: str = Form(..., min_length=5, max_length=50),
    email: EmailStr = Form(...),
    tu_file: UploadFile = File(...),
):
    """Сценарий D: Запрос коммерческого предложения.

    Принимает контактные данные и файл ТУ, отправляет письмо инженеру.
    Заявка в БД не создаётся.
    """
    tu_bytes = await tu_file.read(_MAX_TU_SIZE + 1)
    if len(tu_bytes) > _MAX_TU_SIZE:
        raise HTTPException(status_code=413, detail="Файл слишком большой (максимум 20 МБ)")

    tu_filename = tu_file.filename or "tu.pdf"

    ok = send_kp_request_notification(
        organization=organization,
        responsible_name=responsible_name,
        phone=phone,
        email=email,
        tu_filename=tu_filename,
        tu_bytes=tu_bytes,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Не удалось отправить запрос. Попробуйте позже.")

    return SimpleResponse(
        success=True,
        message="Запрос КП принят. Мы свяжемся с вами в ближайшее время.",
    )


# ── Клиентская страница загрузки (публичная) ─────────────────────────────────


@router.get("/orders/{order_id}/upload-page", response_model=UploadPageInfo)
async def get_upload_page_info(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Информация для клиентской страницы загрузки файлов.

    Клиент получает ссылку в письме:
    https://yourdomain.ru/upload/<order_id>
    """
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    files = await svc.get_files_by_order(order_id)

    await svc.fix_legacy_client_document_params(order)

    if order.status in (
        OrderStatus.WAITING_CLIENT_INFO,
        OrderStatus.CLIENT_INFO_RECEIVED,
    ):
        missing = list(CLIENT_DOCUMENT_PARAM_CODES)
    else:
        missing = order.missing_params or []

    parsed_params: dict | None = None
    survey_data: dict | None = None
    if order.order_type == OrderType.CUSTOM:
        if order.parsed_params:
            parsed_params = order.parsed_params
        if order.survey_data is not None:
            survey_data = order.survey_data

    return UploadPageInfo(
        order_id=order.id,
        client_name=order.client_name,
        order_status=order.status.value,
        order_type=order.order_type.value,
        missing_params=missing,
        files_uploaded=files,
        parsed_params=parsed_params,
        survey_data=survey_data,
    )


@router.post(
    "/orders/{order_id}/upload-tu",
    response_model=FileResponse,
    status_code=201,
)
async def client_upload_tu(
    order_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Публичная загрузка ТУ для новой заявки (страница upload.html).

    Принимает только категорию TU; заявка должна быть в статусе ``new``.
    """
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status != OrderStatus.NEW:
        raise HTTPException(
            status_code=400,
            detail="Загрузка технических условий доступна только для новой заявки",
        )

    try:
        order_file = await svc.upload_file(order_id, FileCategory.TU, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return order_file


@router.post("/orders/{order_id}/submit", response_model=PipelineResponse)
async def client_submit_new_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Публичный запуск парсинга ТУ после загрузки файла (страница upload.html).

    Те же проверки, что у ``POST /pipeline/{id}/start``, без админского ключа.
    """
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.status != OrderStatus.NEW:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя запустить обработку: текущий статус {order.status.value}",
        )

    tu_files = await svc.get_files_by_order(order_id, category=FileCategory.TU)
    if not tu_files:
        raise HTTPException(
            status_code=400,
            detail="Сначала загрузите файл технических условий",
        )

    task = start_tu_parsing.delay(str(order_id))

    return PipelineResponse(
        message="Обработка запущена",
        order_id=order_id,
        task_id=task.id,
    )


@router.post("/orders/{order_id}/survey", response_model=SimpleResponse)
async def save_survey(
    order_id: uuid.UUID,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """Публичное сохранение данных опросного листа (только для custom-заказов)."""
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if order.order_type != OrderType.CUSTOM:
        raise HTTPException(
            status_code=400,
            detail="Опросный лист не требуется для экспресс-заказа",
        )

    if order.status not in _SURVEY_SAVE_ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"Сохранение опроса недоступно в статусе «{order.status.value}»",
        )

    order.survey_data = body
    db.add(order)
    await db.commit()

    return SimpleResponse(success=True, message="Опросный лист сохранён")
