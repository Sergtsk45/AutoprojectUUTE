"""API-эндпоинты для форм лендинга.

Публичные (без авторизации) — вызываются фронтендом.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import OrderService
from app.schemas import OrderCreate

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
