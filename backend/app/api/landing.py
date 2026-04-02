"""API-эндпоинты для форм лендинга.

Публичные (без авторизации) — вызываются фронтендом.
"""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import FileCategory, OrderStatus
from app.services import OrderService
from app.services.tasks import start_tu_parsing
from app.schemas import FileResponse, OrderCreate, PipelineResponse, UploadPageInfo

router = APIRouter(prefix="/landing", tags=["landing"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class SampleRequest(BaseModel):
    email: EmailStr


class OrderRequest(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=255)
    client_email: EmailStr
    client_phone: str | None = Field(None, max_length=50)
    client_organization: str | None = Field(None, max_length=255)
    object_address: str | None = None
    circuits: int | None = Field(None, ge=1, le=10)
    price: int | None = None


class OrderCreatedResponse(BaseModel):
    order_id: str
    upload_url: str
    message: str


class PartnershipRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    company: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=5, max_length=50)


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
    )
    order = await svc.create_order(order_data)

    # Уведомление инженеру (синхронно через отдельную сессию)
    try:
        with SyncSession() as sync_session:
            sync_order = _get_order(sync_session, order.id)
            if sync_order:
                send_new_order_notification(
                    sync_session, sync_order,
                    circuits=data.circuits,
                    price=data.price,
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

    return UploadPageInfo(
        order_id=order.id,
        client_name=order.client_name,
        order_status=order.status.value,
        missing_params=order.missing_params or [],
        files_uploaded=files,
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
