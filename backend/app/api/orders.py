import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_admin_key
from app.core.database import get_db
from app.models import OrderStatus, FileCategory
from app.schemas import (
    OrderCreate,
    OrderStatusUpdate,
    OrderResponse,
    OrderListItem,
    FileResponse,
    build_order_response,
)
from app.services import OrderService

router = APIRouter(prefix="/orders", tags=["orders"], dependencies=[Depends(verify_admin_key)])


def get_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(db)


# ── Создание заявки ──────────────────────────────────────────────────────────


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    data: OrderCreate,
    svc: OrderService = Depends(get_service),
):
    """Создать заявку.

    Вызывается формой на лендинге после того, как клиент
    заполнил контактные данные.
    """
    order = await svc.create_order(data)
    # Перезагружаем с файлами и письмами для корректной сериализации
    order = await svc.get_order(order.id)
    return build_order_response(order)


# ── Получение заявки ─────────────────────────────────────────────────────────


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    svc: OrderService = Depends(get_service),
):
    """Получить полную информацию о заявке."""
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return build_order_response(order)


# ── Список заявок ────────────────────────────────────────────────────────────


@router.get("", response_model=list[OrderListItem])
async def list_orders(
    status: OrderStatus | None = Query(None, description="Фильтр по статусу"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: OrderService = Depends(get_service),
):
    """Список заявок (для админки)."""
    return await svc.list_orders(status=status, limit=limit, offset=offset)


# ── Смена статуса ────────────────────────────────────────────────────────────


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: uuid.UUID,
    data: OrderStatusUpdate,
    svc: OrderService = Depends(get_service),
):
    """Сменить статус заявки.

    Используется:
    - оркестратором (Celery-задачи) для автоматических переходов
    - инженером на этапе review для одобрения / возврата
    """
    try:
        order = await svc.update_status(order_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    order = await svc.get_order(order.id)
    return build_order_response(order)


# ── Загрузка файла ТУ (при создании заявки) ──────────────────────────────────


@router.post("/{order_id}/files", response_model=FileResponse, status_code=201)
async def upload_file(
    order_id: uuid.UUID,
    category: FileCategory = Query(..., description="Категория файла"),
    file: UploadFile = File(...),
    svc: OrderService = Depends(get_service),
):
    """Загрузить файл к заявке.

    Используется:
    - клиентом при создании заявки (ТУ)
    - клиентом через страницу загрузки (план, схема)
    - системой для сохранения сгенерированных файлов
    """
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    try:
        order_file = await svc.upload_file(order_id, category, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return order_file


# ── Список файлов заявки ─────────────────────────────────────────────────────


@router.get("/{order_id}/files", response_model=list[FileResponse])
async def list_files(
    order_id: uuid.UUID,
    category: FileCategory | None = Query(None),
    svc: OrderService = Depends(get_service),
):
    """Получить файлы заявки."""
    return await svc.get_files_by_order(order_id, category=category)
