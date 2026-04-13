"""
@file: calculator_config.py
@description: API-роутер настроечной БД вычислителя
@dependencies: calculator_config_service.py, models.py
@created: 2026-04-12
"""

import asyncio
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_admin_key
from app.core.database import get_db
from app.models.models import CalculatorConfig, Order, OrderType
from app.services import calculator_config_service as svc

router = APIRouter(
    prefix="/admin/orders/{order_id}",
    tags=["calculator-config"],
    dependencies=[Depends(verify_admin_key)],
)


def _config_to_dict(config: CalculatorConfig) -> dict:
    return {
        "id": config.id,
        "calculator_type": config.calculator_type,
        "config_data": config.config_data,
        "status": config.status,
        "total_params": config.total_params,
        "filled_params": config.filled_params,
        "missing_required": config.missing_required,
        "client_requested_params": config.client_requested_params,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


async def _get_order_or_404(order_id: uuid.UUID, db: AsyncSession) -> Order:
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return order


async def _get_config(order_id: uuid.UUID, db: AsyncSession) -> CalculatorConfig | None:
    stmt = select(CalculatorConfig).where(CalculatorConfig.order_id == order_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


@router.get("/calc-config")
async def get_calc_config(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Получить конфиг вычислителя для заявки или шаблон если конфиг не инициализирован."""
    order = await _get_order_or_404(order_id, db)
    config = await _get_config(order_id, db)

    if config is None:
        if order.order_type == OrderType.EXPRESS:
            # Express: определяем тип только через parsed_params (только Эско-Терра)
            calculator_type = svc.resolve_calculator_type_for_express(order)
            esko_detected = calculator_type == "esko_terra"

            if not esko_detected:
                # Возвращаем шаблон Эско-Терра для ручной инициализации инженером
                try:
                    template = svc.load_template("esko_terra")
                except ValueError:
                    template = None
                return {
                    "config": None,
                    "template": template,
                    "calculator_type": "esko_terra",
                    "status": "not_supported_for_express",
                    "esko_detected": False,
                    "message": "Вычислитель Эско-Терра не обнаружен в ТУ автоматически. Можно инициализировать вручную.",
                }

            try:
                template = svc.load_template("esko_terra")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            return {
                "config": None,
                "template": template,
                "calculator_type": "esko_terra",
                "status": "not_initialized",
                "esko_detected": True,
            }
        else:
            # Custom: определяем тип через survey_data.manufacturer
            survey_data = order.survey_data or {}
            manufacturer = survey_data.get("manufacturer", "")
            calculator_type = svc.MANUFACTURER_TO_CALCULATOR.get(manufacturer)

            if not calculator_type:
                return {
                    "config": None,
                    "template": None,
                    "message": "Производитель не поддерживается или не указан",
                }

            try:
                template = svc.load_template(calculator_type)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            return {
                "config": None,
                "template": template,
                "calculator_type": calculator_type,
                "status": "not_initialized",
            }

    try:
        template = svc.load_template(config.calculator_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "config": _config_to_dict(config),
        "template": template,
        "calculator_type": config.calculator_type,
        "status": config.status,
    }


@router.post("/calc-config/init", status_code=201)
async def init_calc_config(
    order_id: uuid.UUID,
    body: dict = Body(default={}),
    db: AsyncSession = Depends(get_db),
):
    """Инициализировать или переинициализировать конфиг вычислителя."""
    order = await _get_order_or_404(order_id, db)

    # Для express-заявок разрешён только тип esko_terra
    if order.order_type == OrderType.EXPRESS:
        if "calculator_type" in body and body["calculator_type"] != "esko_terra":
            raise HTTPException(
                status_code=400,
                detail=f"Для экспресс-заявки допустим только тип 'esko_terra', получен '{body['calculator_type']}'",
            )
        # Если calculator_type не указан — принудительно используем esko_terra
        body = {**body, "calculator_type": "esko_terra"}

    if "calculator_type" in body:
        calc_type = body["calculator_type"]
        try:
            template = svc.load_template(calc_type)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        config_data = svc.auto_fill(template, order.parsed_params or {}, order.survey_data or {})
        total, filled, missing = svc.compute_fill_stats(template, config_data)

        existing = await _get_config(order_id, db)
        if existing:
            existing.calculator_type = calc_type
            existing.config_data = config_data
            existing.status = "draft"
            existing.total_params = total
            existing.filled_params = filled
            existing.missing_required = missing
            config = existing
        else:
            config = CalculatorConfig(
                order_id=order.id,
                calculator_type=calc_type,
                config_data=config_data,
                status="draft",
                total_params=total,
                filled_params=filled,
                missing_required=missing,
                client_requested_params=[],
            )
            db.add(config)

        await db.commit()
        await db.refresh(config)
    else:
        try:
            config = await svc.init_config(order, db)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    try:
        template = svc.load_template(config.calculator_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "config": _config_to_dict(config),
        "template": template,
        "calculator_type": config.calculator_type,
        "status": config.status,
    }


class CalcConfigUpdateBody(BaseModel):
    params: dict


@router.patch("/calc-config")
async def update_calc_config(
    order_id: uuid.UUID,
    body: CalcConfigUpdateBody,
    db: AsyncSession = Depends(get_db),
):
    """Обновить параметры конфига вычислителя."""
    await _get_order_or_404(order_id, db)

    config = await _get_config(order_id, db)
    if config is None:
        raise HTTPException(status_code=404, detail="Конфиг не инициализирован")

    try:
        config = await svc.update_params(config, body.params, db)
        template = svc.load_template(config.calculator_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "config": _config_to_dict(config),
        "template": template,
        "calculator_type": config.calculator_type,
        "status": config.status,
    }


@router.post("/calc-config/export-pdf")
async def export_calc_config_pdf(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Экспортировать настроечную БД вычислителя в PDF."""
    order = await _get_order_or_404(order_id, db)

    config = await _get_config(order_id, db)
    if config is None:
        raise HTTPException(status_code=404, detail="Конфиг не инициализирован")

    try:
        template = svc.load_template(config.calculator_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    loop = asyncio.get_event_loop()
    pdf_bytes = await loop.run_in_executor(None, svc.export_pdf, config, template, order)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="calc_config_{order_id}.pdf"'},
    )
