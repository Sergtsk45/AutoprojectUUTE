"""
@file: scheme_generator.py
@description: REST API для конфигуратора принципиальных схем теплового пункта.
              Эндпоинты для превью SVG, генерации PDF и получения списка доступных конфигураций.
@dependencies: fastapi, scheme_service, scheme_svg_renderer, scheme_gost_frame, scheme_pdf_renderer
@created: 2026-04-23
"""

import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Order, OrderFile, FileCategory
from app.schemas.scheme import (
    SchemeConfig,
    SchemeGenerateRequest,
    SchemePreviewResponse,
    SchemeTemplateInfo,
)
from app.services.order_service import OrderService
from app.services.scheme_gost_frame import gost_frame_a3
from app.services.scheme_pdf_renderer import render_scheme_pdf
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
        SVG-контент схемы с ГОСТ-рамкой для отображения в браузере
        
    Raises:
        HTTPException 400: Если конфигурация невалидна или комбинация параметров недопустима
    """
    # Подбор типа схемы по конфигурации
    scheme_type = resolve_scheme_type(request.config)
    
    if scheme_type is None:
        raise HTTPException(
            status_code=400,
            detail="Недопустимая комбинация параметров схемы. Проверьте соответствие "
                   "конфигурации одному из 8 типовых вариантов."
        )
    
    # Генерация SVG контента схемы
    params = request.params or extract_scheme_params_from_parsed({})
    scheme_content = render_scheme(scheme_type, params)
    
    # Обертка в ГОСТ-рамку для превью
    stamp_data = {
        "project_number": params.project_number or "",
        "object_name": params.object_address or "",
        "sheet_name": "Схема функциональная",
        "sheet_title": "Узел учета тепловой энергии",
        "company": params.company_name or "",
        "executor": params.engineer_name or "",
        "stage": "П",
        "sheet_num": "1",
        "total_sheets": "1",
        "format": "A3",
    }
    
    svg_with_frame = gost_frame_a3(scheme_content, stamp_data)
    
    # Получение человекочитаемой метки схемы
    from app.services.scheme_service import SCHEME_LABELS
    scheme_label = SCHEME_LABELS.get(scheme_type, {}).get("label", scheme_type.value)
    
    return SchemePreviewResponse(
        scheme_type=scheme_type,
        scheme_label=scheme_label,
        svg_content=svg_with_frame,
    )


# ── POST /api/v1/schemes/{order_id}/generate ──────────────────────────────────


@router.post("/{order_id}/generate")
async def generate_scheme_pdf(
    order_id: uuid.UUID,
    request: SchemeGenerateRequest,
    svc: OrderService = Depends(get_order_service),
):
    """
    Генерирует PDF схемы и сохраняет как файл заявки.
    
    Args:
        order_id: UUID заявки
        request: Конфигурация схемы и параметры
        
    Returns:
        Информация о сохраненном файле (id, category, filename)
        
    Raises:
        HTTPException 404: Заявка не найдена
        HTTPException 400: Невалидная конфигурация схемы
    """
    # Проверка существования заявки
    order = await svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    # Подбор типа схемы
    scheme_type = resolve_scheme_type(request.config)
    if scheme_type is None:
        raise HTTPException(
            status_code=400,
            detail="Недопустимая комбинация параметров схемы"
        )
    
    # Извлечение параметров из parsed_params заявки или использование переданных
    if request.params is None and order.parsed_params:
        params = extract_scheme_params_from_parsed(order.parsed_params)
    else:
        params = request.params or extract_scheme_params_from_parsed({})
    
    # Автозаполнение из Order
    if not params.project_number and order.id:
        params.project_number = f"УУТЭ-{str(order.id)[:8].upper()}"
    if not params.object_address and order.object_address:
        params.object_address = order.object_address
    if not params.company_name and order.client_organization:
        params.company_name = order.client_organization
    
    # Генерация SVG
    scheme_content = render_scheme(scheme_type, params)
    
    # Формирование данных штампа
    stamp_data = {
        "project_number": params.project_number or "",
        "object_name": params.object_address or "",
        "sheet_name": "Схема функциональная",
        "sheet_title": "Узел учета тепловой энергии",
        "company": params.company_name or "",
        "gip": "",  # TODO: Добавить в настройки компании
        "executor": params.engineer_name or "",
        "inspector": "",  # TODO: Добавить в настройки
        "stage": "П",
        "sheet_num": "1",
        "total_sheets": "1",
        "format": "A3",
    }
    
    # SVG с ГОСТ-рамкой
    svg_with_frame = gost_frame_a3(scheme_content, stamp_data)
    
    # Генерация PDF
    pdf_bytes = render_scheme_pdf(svg_with_frame, stamp_data, "A3")
    
    # Сохранение файла
    file_uuid = uuid.uuid4().hex[:12]
    filename = f"heat_scheme_{file_uuid}.pdf"
    
    # Путь: uploads/<order_id>/heat_scheme/<filename>
    from app.core.config import settings
    relative_path = f"{order_id}/heat_scheme/{filename}"
    full_path = settings.upload_dir / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Запись PDF на диск
    async with aiofiles.open(full_path, "wb") as f:
        await f.write(pdf_bytes)
    
    # Создание записи в БД
    order_file = OrderFile(
        order_id=order_id,
        category=FileCategory.HEAT_SCHEME,
        original_filename=filename,
        storage_path=relative_path,
        content_type="application/pdf",
        file_size=len(pdf_bytes),
    )
    svc.db.add(order_file)
    
    # Сохранение конфигурации в survey_data
    if order.survey_data is None:
        order.survey_data = {}
    
    order.survey_data["scheme_config"] = {
        "connection_type": request.config.connection_type,
        "has_valve": request.config.has_valve,
        "has_gwp": request.config.has_gwp,
        "has_ventilation": request.config.has_ventilation,
        "scheme_type": scheme_type.value,
        "generated_at": str(order_file.created_at) if hasattr(order_file, 'created_at') else None,
    }
    
    await svc.db.commit()
    await svc.db.refresh(order_file)
    
    return {
        "file_id": str(order_file.id),
        "category": order_file.category.value,
        "filename": order_file.original_filename,
        "file_size": order_file.file_size,
        "scheme_type": scheme_type.value,
        "message": "PDF схемы успешно сгенерирован и сохранен",
    }


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
