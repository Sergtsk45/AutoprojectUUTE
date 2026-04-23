"""Админские утилиты: скачивание файлов, статистика."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_admin_key
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Order, OrderFile, OrderStatus

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_key)],
)


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Скачать файл заявки по его ID."""
    stmt = select(OrderFile).where(OrderFile.id == file_id)
    result = await db.execute(stmt)
    order_file = result.scalar_one_or_none()

    if order_file is None:
        raise HTTPException(status_code=404, detail="Файл не найден")

    full_path = settings.upload_dir / order_file.storage_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден на диске")

    return FileResponse(
        path=str(full_path),
        filename=order_file.original_filename,
        media_type=order_file.content_type or "application/octet-stream",
    )


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Простая статистика для дашборда."""
    result = await db.execute(select(Order.status, func.count(Order.id)).group_by(Order.status))
    status_counts = {row[0].value: row[1] for row in result.all()}
    total = sum(status_counts.values())

    return {
        "total": total,
        "by_status": status_counts,
    }
