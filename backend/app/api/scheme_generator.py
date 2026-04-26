"""
@file: scheme_generator.py
@description: REST API для конфигуратора принципиальных схем теплового пункта.
              Эндпоинты для демонстрационного SVG-превью и получения списка доступных конфигураций.
@dependencies: fastapi, scheme_service, scheme_svg_renderer
@created: 2026-04-23
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import FileCategory, OrderFile
from app.schemas.scheme import (
    SchemeGenerateRequest,
    SchemePreviewResponse,
    SchemeTemplateInfo,
)
from app.services.order_service import OrderService
from app.services.scheme_service import (
    extract_scheme_params_from_parsed,
    get_available_templates,
    resolve_scheme_type,
)
from app.services.scheme_svg_renderer import render_scheme

router = APIRouter(prefix="/schemes", tags=["schemes"])


def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    """DI для OrderService."""
    return OrderService(db)


def _wrap_demo_preview_svg(content_svg: str) -> str:
    """Оборачивает схему в standalone SVG без ГОСТ-рамки и штампа."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 1150 820" width="100%" height="auto" '
        'role="img" aria-label="Предварительный просмотр выбранной схемы">'
        f"{content_svg}</svg>"
    )


# ── GET /api/v1/schemes/templates ────────────────────────────────────────────


@router.get("/templates", response_model=list[SchemeTemplateInfo])
async def list_scheme_templates():
    """
    Возвращает список всех доступных конфигураций схем (8 типов).

    Используется UI для отображения доступных вариантов схем клиенту.
    """
    return get_available_templates()


# ── POST /api/v1/schemes/preview ──────────────────────────────────────────────


@router.post("/preview", response_model=SchemePreviewResponse)
async def preview_scheme(request: SchemeGenerateRequest):
    """
    Генерирует превью SVG схемы по конфигурации.

    Args:
        request: Конфигурация схемы (SchemeConfig) и опциональные параметры (SchemeParams)

    Returns:
        SVG-контент схемы без ГОСТ-рамки для отображения в браузере

    Raises:
        HTTPException 400: Если конфигурация невалидна или комбинация параметров недопустима
    """
    # Подбор типа схемы по конфигурации
    scheme_type = resolve_scheme_type(request.config)

    if scheme_type is None:
        raise HTTPException(
            status_code=400,
            detail="Недопустимая комбинация параметров схемы. Проверьте соответствие "
            "конфигурации одному из 8 типовых вариантов.",
        )

    # Генерация SVG контента схемы
    params = request.params or extract_scheme_params_from_parsed({})
    scheme_content = render_scheme(scheme_type, params)

    # Получение человекочитаемой метки схемы
    from app.services.scheme_service import SCHEME_LABELS

    scheme_label = SCHEME_LABELS.get(scheme_type, {}).get("label", scheme_type.value)

    return SchemePreviewResponse(
        scheme_type=scheme_type,
        scheme_label=scheme_label,
        svg_content=_wrap_demo_preview_svg(scheme_content),
    )


# ── POST /api/v1/schemes/{order_id}/generate ──────────────────────────────────


@router.post("/{order_id}/generate")
async def generate_scheme_pdf(
    order_id: uuid.UUID,
    request: SchemeGenerateRequest,
):
    """Клиентская PDF-генерация отключена: конфигуратор только показывает превью."""
    del order_id, request
    raise HTTPException(
        status_code=410,
        detail="PDF-генерация схемы на клиентской странице отключена. "
        "Сейчас конфигуратор используется только для демонстрационного предпросмотра.",
    )


# ── GET /api/v1/schemes/{order_id}/files/{file_id}/download ──────────────────


@router.get("/{order_id}/files/{file_id}/download")
async def download_generated_scheme_file(
    order_id: uuid.UUID,
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Публичное скачивание PDF принципиальной схемы клиентом.

    Доступ ограничен UUID заявки и только категорией ``heat_scheme``: другие
    файлы заявки остаются за admin/API-флоу.
    """
    stmt = select(OrderFile).where(
        OrderFile.id == file_id,
        OrderFile.order_id == order_id,
        OrderFile.category == FileCategory.HEAT_SCHEME,
    )
    result = await db.execute(stmt)
    order_file = result.scalar_one_or_none()

    if order_file is None:
        raise HTTPException(status_code=404, detail="Схема не найдена")

    full_path = settings.upload_dir / order_file.storage_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Файл схемы не найден на диске")

    return FileResponse(
        path=str(full_path),
        filename=order_file.original_filename,
        media_type=order_file.content_type or "application/pdf",
    )


# ── GET /api/v1/schemes/{order_id}/config ──────────────────────────────────────


@router.get("/{order_id}/config")
async def get_scheme_config(
    order_id: uuid.UUID,
    svc: OrderService = Depends(get_order_service),
):
    """
    Возвращает сохраненную конфигурацию схемы из survey_data заявки.

    Args:
        order_id: UUID заявки

    Returns:
        Конфигурация схемы из survey_data или None, если схема еще не сгенерирована

    Raises:
        HTTPException 404: Заявка не найдена
    """
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    scheme_config = None
    if order.survey_data and "scheme_config" in order.survey_data:
        scheme_config = order.survey_data["scheme_config"]

    # Автозаполнение из parsed_params
    suggested_config = None
    if order.parsed_params:
        params = extract_scheme_params_from_parsed(order.parsed_params)
        # TODO: Реализовать логику автозаполнения конфигурации из parsed_params
        # Это требует анализа parsed_params.connection.connection_type и других полей

    return {
        "order_id": str(order_id),
        "scheme_config": scheme_config,
        "suggested_config": suggested_config,
        "has_generated_scheme": scheme_config is not None,
    }
