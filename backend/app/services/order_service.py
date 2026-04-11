import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import Order, OrderFile, OrderStatus, OrderType, FileCategory
from app.schemas import OrderCreate, OrderStatusUpdate
from app.services.param_labels import (
    CLIENT_DOCUMENT_PARAM_CODES,
    client_document_list_needs_migration,
)


class OrderService:
    """Бизнес-логика работы с заявками."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Создание заявки ──────────────────────────────────────────────────

    async def create_order(self, data: OrderCreate) -> Order:
        """Создать новую заявку."""
        order = Order(
            client_name=data.client_name,
            client_email=data.client_email,
            client_phone=data.client_phone,
            client_organization=data.client_organization,
            object_address=data.object_address,
            object_city=data.object_city,
            status=OrderStatus.NEW,
            order_type=OrderType(data.order_type) if data.order_type else OrderType.EXPRESS,
        )
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    # ── Получение заявки ─────────────────────────────────────────────────

    async def get_order(self, order_id: uuid.UUID) -> Order | None:
        """Получить заявку со всеми связями."""
        stmt = (
            select(Order)
            .options(selectinload(Order.files), selectinload(Order.emails))
            .where(Order.id == order_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_orders(
        self,
        status: OrderStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        """Список заявок с фильтрацией по статусу."""
        stmt = select(Order).order_by(Order.created_at.desc()).limit(limit).offset(offset)
        if status:
            stmt = stmt.where(Order.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def fix_legacy_client_document_params(self, order: Order) -> None:
        """Убрать из БД устаревшие коды (floor_plan и т.д.): заменить список на канонические четыре.

        Не трогает заявки, где missing_params уже подмножество четырёх кодов после «Готово».
        """
        if order.status not in (
            OrderStatus.WAITING_CLIENT_INFO,
            OrderStatus.CLIENT_INFO_RECEIVED,
        ):
            return
        if not client_document_list_needs_migration(order.missing_params):
            return
        order.missing_params = list(CLIENT_DOCUMENT_PARAM_CODES)
        await self.db.commit()
        await self.db.refresh(order)

    # ── Смена статуса ────────────────────────────────────────────────────

    async def update_status(
        self,
        order_id: uuid.UUID,
        data: OrderStatusUpdate,
    ) -> Order:
        """Сменить статус заявки с проверкой допустимости перехода."""
        order = await self.get_order(order_id)
        if order is None:
            raise ValueError(f"Заявка {order_id} не найдена")

        if not order.can_transition_to(data.status):
            raise ValueError(
                f"Переход {order.status.value} → {data.status.value} недопустим"
            )

        order.status = data.status
        if data.reviewer_comment is not None:
            order.reviewer_comment = data.reviewer_comment

        await self.db.commit()
        await self.db.refresh(order)
        return order

    # ── Загрузка файлов ──────────────────────────────────────────────────

    async def upload_file(
        self,
        order_id: uuid.UUID,
        category: FileCategory,
        file: UploadFile,
    ) -> OrderFile:
        """Сохранить файл на диск и создать запись в БД."""
        order = await self.get_order(order_id)
        if order is None:
            raise ValueError(f"Заявка {order_id} не найдена")

        # Формируем путь: uploads/<order_id>/<category>/<uuid>_<filename>
        file_uuid = uuid.uuid4().hex[:12]
        safe_filename = file.filename or "unnamed"
        relative_path = f"{order_id}/{category.value}/{file_uuid}_{safe_filename}"
        full_path = settings.upload_dir / relative_path

        # Создаём директорию
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Пишем файл
        content = await file.read()
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)

        # Запись в БД
        order_file = OrderFile(
            order_id=order_id,
            category=category,
            original_filename=safe_filename,
            storage_path=relative_path,
            content_type=file.content_type,
            file_size=len(content),
        )
        self.db.add(order_file)
        await self.db.commit()
        await self.db.refresh(order_file)
        return order_file

    async def get_files_by_order(
        self,
        order_id: uuid.UUID,
        category: FileCategory | None = None,
    ) -> list[OrderFile]:
        """Получить файлы заявки, опционально по категории."""
        stmt = select(OrderFile).where(OrderFile.order_id == order_id)
        if category:
            stmt = stmt.where(OrderFile.category == category)
        stmt = stmt.order_by(OrderFile.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
