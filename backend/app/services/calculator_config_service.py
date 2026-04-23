"""
@file: calculator_config_service.py
@description: Сервис инициализации и автозаполнения настроечной БД вычислителя
@dependencies: models.py, calculator_templates/*.json
@created: 2026-04-12
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.repositories.order_jsonb import (
    get_parsed_params,
    get_parsed_params_dict,
    get_survey_data,
    get_survey_data_dict,
)

MANUFACTURER_TO_CALCULATOR = {
    "esko": "esko_terra",
    "teplokom": "tv7",
    "logika": "spt941",
}

ALLOWED_CALCULATOR_TYPES = frozenset(
    MANUFACTURER_TO_CALCULATOR.values()
)  # {'tv7', 'spt941', 'esko_terra'}

# Маркеры Эско-Терра в поле metering.heat_calculator_model
ESKO_MARKERS = frozenset({"эско", "терра", "эско-3э", "esko", "terra", "3э"})


def resolve_calculator_type_for_express(order) -> str | None:
    """Определить тип вычислителя для express-заявки по parsed_params.

    Проверяет metering.heat_calculator_model на маркеры Эско-Терра.
    Возвращает 'esko_terra' если обнаружены, иначе None.
    """
    parsed = get_parsed_params(order)
    if parsed is None:
        return None
    model = (parsed.metering.heat_calculator_model or "").lower()
    if any(marker in model for marker in ESKO_MARKERS):
        return "esko_terra"
    return None


TEMPLATES_DIR = Path(__file__).parent.parent.parent / "calculator_templates"

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def load_template(calculator_type: str) -> dict:
    if calculator_type not in ALLOWED_CALCULATOR_TYPES:
        raise ValueError(
            f"Неизвестный тип вычислителя: {calculator_type!r}. "
            f"Допустимые: {sorted(ALLOWED_CALCULATOR_TYPES)}"
        )
    path = TEMPLATES_DIR / f"{calculator_type}.json"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"Шаблон для '{calculator_type}' не найден")
    except json.JSONDecodeError:
        raise ValueError(f"Повреждён шаблон '{calculator_type}'")


def get_nested(data: dict, path: str) -> Any:
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current


def execute_auto_rule(
    rule_name: str,
    parsed_params: dict,
    survey_data: dict,
    current_values: dict,
) -> Any:
    if rule_name == "map_tu_pressure_supply":
        return get_nested(parsed_params, "coolant.supply_pressure_kgcm2")

    if rule_name == "map_tu_pressure_return":
        return get_nested(parsed_params, "coolant.return_pressure_kgcm2")

    if rule_name == "map_tu_supply_temp":
        return get_nested(parsed_params, "coolant.supply_temp")

    if rule_name == "map_tu_return_temp":
        return get_nested(parsed_params, "coolant.return_temp")

    if rule_name == "map_survey_tcw":
        return survey_data.get("tcw")

    if rule_name == "calculate_gdog":
        Q = get_nested(parsed_params, "heat_loads.total_load")
        t1 = get_nested(parsed_params, "coolant.supply_temp")
        t2 = get_nested(parsed_params, "coolant.return_temp")
        if Q is not None and t1 is not None and t2 is not None and (t1 - t2) > 0:
            return round(Q * 1000 / (t1 - t2), 3)
        return None

    if rule_name == "derive_si":
        system_type = get_nested(parsed_params, "connection.system_type") or ""
        is_closed = "закрытая" in system_type or (
            "открытая" not in system_type and "двухтрубная" in system_type
        )
        calc_type = current_values.get("_calculator_type", "tv7")
        if calc_type == "tv7":
            return "1" if is_closed else "4"
        elif calc_type == "spt941":
            return "0" if is_closed else "2"
        elif calc_type == "esko_terra":
            return "0" if is_closed else "1"
        return None

    if rule_name == "derive_ft":
        si = current_values.get("SI") or current_values.get("SI_M1")
        calc_type = current_values.get("_calculator_type", "tv7")
        if si is None:
            return None
        try:
            si_int = int(si)
        except (ValueError, TypeError):
            return None
        if calc_type == "tv7":
            if si_int == 1:
                return "1"
            elif si_int == 2:
                return "2"
            elif si_int in (3, 4, 5, 6):
                return "3"
        else:
            if si_int == 0:
                return "1"
            return "2"
        return None

    if rule_name == "derive_ht":
        model = get_nested(parsed_params, "metering.temp_sensor_model") or ""
        model_up = model.upper()
        if "КТСН" in model_up or "100П" in model_up:
            return "0"
        elif "PT100" in model_up or "PT 100" in model_up:
            return "1"
        elif "100М" in model_up:
            return "2"
        return None

    return None


def auto_fill(template: dict, parsed_params: dict, survey_data: dict) -> dict:
    """Пройти по всем параметрам шаблона, выполнить auto_rule, вернуть dict {param_id: value}."""
    result = {}
    calculator_type = template["calculator_id"]

    for group in template["groups"]:
        for param in group["params"]:
            if param.get("default") is not None:
                result[param["id"]] = param["default"]

            if param.get("auto_rule"):
                current_with_type = {**result, "_calculator_type": calculator_type}
                val = execute_auto_rule(
                    param["auto_rule"],
                    parsed_params or {},
                    survey_data or {},
                    current_with_type,
                )
                if val is not None:
                    result[param["id"]] = str(val) if not isinstance(val, str) else val

    return result


def compute_fill_stats(template: dict, config_data: dict) -> tuple[int, int, list[str]]:
    """Подсчёт: (total_params, filled_params, missing_required_ids)."""
    total = 0
    filled = 0
    missing = []

    for group in template["groups"]:
        for param in group["params"]:
            total += 1
            val = config_data.get(param["id"])
            has_value = val is not None and str(val).strip() != ""
            if has_value:
                filled += 1
            elif param.get("required", False):
                missing.append(param["id"])

    return total, filled, missing


async def init_config(order, db: AsyncSession):
    """Создать или пересоздать конфиг для заявки.
    Определяет calculator_type из survey_data.manufacturer.
    """
    from app.models.models import CalculatorConfig

    # Типизированное чтение survey_data; auto_fill принимает сырой dict.
    survey = get_survey_data(order)
    manufacturer = survey.manufacturer if survey is not None else None
    calculator_type = MANUFACTURER_TO_CALCULATOR.get(manufacturer or "")

    if not calculator_type:
        raise ValueError(
            f"Производитель '{manufacturer}' не поддерживается. "
            f"Доступно: {list(MANUFACTURER_TO_CALCULATOR.keys())}"
        )

    template = load_template(calculator_type)
    config_data = auto_fill(
        template,
        get_parsed_params_dict(order),
        get_survey_data_dict(order),
    )
    total, filled, missing = compute_fill_stats(template, config_data)

    stmt = select(CalculatorConfig).where(CalculatorConfig.order_id == order.id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.calculator_type = calculator_type
        existing.config_data = config_data
        existing.status = "draft"
        existing.total_params = total
        existing.filled_params = filled
        existing.missing_required = missing
        flag_modified(existing, "config_data")
        flag_modified(existing, "missing_required")
        await db.commit()
        await db.refresh(existing)
        return existing

    config = CalculatorConfig(
        order_id=order.id,
        calculator_type=calculator_type,
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
    return config


async def update_params(config, params_dict: dict, db: AsyncSession):
    """Обновить параметры, пересчитать статистику."""
    new_data = {**config.config_data, **params_dict}
    template = load_template(config.calculator_type)
    total, filled, missing = compute_fill_stats(template, new_data)

    config.config_data = new_data
    config.total_params = total
    config.filled_params = filled
    config.missing_required = missing
    flag_modified(config, "config_data")
    flag_modified(config, "missing_required")
    if not missing:
        config.status = "complete"

    await db.commit()
    await db.refresh(config)
    return config


def init_config_sync(order, session) -> "CalculatorConfig":
    """Синхронная версия init_config для Celery-задач (express-заявки).

    Определяет тип вычислителя через resolve_calculator_type_for_express,
    инициализирует или перезаписывает конфиг в той же sync-сессии.
    Raises ValueError если тип не определён.
    """
    from app.models.models import CalculatorConfig
    from sqlalchemy import select as sa_select
    from sqlalchemy.orm.attributes import flag_modified as fm

    calculator_type = resolve_calculator_type_for_express(order)
    if not calculator_type:
        raise ValueError(
            "Тип вычислителя не определён: маркеры Эско-Терра не найдены в parsed_params"
        )

    template = load_template(calculator_type)
    config_data = auto_fill(
        template,
        get_parsed_params_dict(order),
        get_survey_data_dict(order),
    )
    total, filled, missing = compute_fill_stats(template, config_data)

    existing = session.execute(
        sa_select(CalculatorConfig).where(CalculatorConfig.order_id == order.id)
    ).scalar_one_or_none()

    if existing:
        existing.calculator_type = calculator_type
        existing.config_data = config_data
        existing.status = "draft"
        existing.total_params = total
        existing.filled_params = filled
        existing.missing_required = missing
        fm(existing, "config_data")
        fm(existing, "missing_required")
        session.commit()
        session.refresh(existing)
        return existing

    config = CalculatorConfig(
        order_id=order.id,
        calculator_type=calculator_type,
        config_data=config_data,
        status="draft",
        total_params=total,
        filled_params=filled,
        missing_required=missing,
        client_requested_params=[],
    )
    session.add(config)
    session.commit()
    session.refresh(config)
    return config


def export_pdf(config, template: dict, order) -> bytes:
    """Генерация PDF настроечной БД в формате Приложения Г РЭ прибора."""
    import fitz

    use_custom_font = os.path.exists(FONT_PATH)

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    if use_custom_font:
        page.insert_font(fontname="dvu", fontfile=FONT_PATH)
        font_name = "dvu"
    else:
        font_name = "helv"

    BLACK = (0, 0, 0)
    GRAY = (0.5, 0.5, 0.5)

    y = 40
    margin_l = 40
    margin_r = 555

    def insert_text(pg, pos, text, fontsize, color=BLACK, bold=False):
        fn = font_name
        if not use_custom_font and bold:
            fn = "hebo"
        pg.insert_text(pos, text, fontsize=fontsize, fontname=fn, color=color)

    # ─── Шапка ───────────────────────────────────────────────────────────────
    insert_text(page, (margin_l, y), "НАСТРОЕЧНАЯ БАЗА ДАННЫХ ВЫЧИСЛИТЕЛЯ", fontsize=14)
    y += 20

    calc_name = template.get("calculator_name", config.calculator_type)
    insert_text(page, (margin_l, y), calc_name, fontsize=12)
    y += 16

    re_version = template.get("re_version", "")
    if re_version:
        insert_text(page, (margin_l, y), f"РЭ: {re_version}", fontsize=9, color=GRAY)
        y += 14

    y += 4
    page.draw_line((margin_l, y), (margin_r, y), color=GRAY, width=0.5)
    y += 8

    obj_addr = getattr(order, "object_address", "") or ""
    client_name = getattr(order, "client_name", "") or ""
    client_org = getattr(order, "client_organization", "") or ""

    info_lines = []
    if obj_addr:
        info_lines.append(f"Объект: {obj_addr}")
    if client_org:
        info_lines.append(f"Организация: {client_org}")
    elif client_name:
        info_lines.append(f"Заявитель: {client_name}")

    for line in info_lines:
        insert_text(page, (margin_l, y), line, fontsize=9)
        y += 13

    y += 8
    page.draw_line((margin_l, y), (margin_r, y), color=BLACK, width=1)
    y += 12

    # ─── Таблица параметров ───────────────────────────────────────────────────
    has_dual = template.get("has_dual_db", False)

    col_id = margin_l
    col_label = margin_l + 45
    col_val = margin_l + 320
    col_val2 = margin_l + 420
    col_right = margin_r

    page.draw_rect(
        fitz.Rect(margin_l, y, margin_r, y + 16),
        color=GRAY,
        fill=(0.85, 0.85, 0.85),
    )
    insert_text(page, (col_id + 2, y + 11), "Обозн.", fontsize=8)
    insert_text(page, (col_label + 2, y + 11), "Параметр", fontsize=8)
    if has_dual:
        insert_text(page, (col_val + 2, y + 11), "БД1 (зима)", fontsize=8)
        insert_text(page, (col_val2 + 2, y + 11), "БД2 (лето)", fontsize=8)
    else:
        insert_text(page, (col_val + 2, y + 11), "Значение", fontsize=8)
    y += 16

    config_data = config.config_data or {}

    for group in template["groups"]:
        if y > 790:
            page = doc.new_page(width=595, height=842)
            if use_custom_font:
                page.insert_font(fontname="dvu", fontfile=FONT_PATH)
            y = 40

        insert_text(page, (col_id, y + 10), group["label"], fontsize=9, bold=True)
        y += 14
        page.draw_line((margin_l, y), (margin_r, y), color=GRAY, width=0.3)

        for i, param in enumerate(group["params"]):
            if y > 800:
                page = doc.new_page(width=595, height=842)
                if use_custom_font:
                    page.insert_font(fontname="dvu", fontfile=FONT_PATH)
                y = 40

            row_h = 14
            bg = (0.97, 0.97, 0.97) if i % 2 == 0 else (1, 1, 1)
            page.draw_rect(fitz.Rect(margin_l, y, margin_r, y + row_h), fill=bg, color=None)

            label_text = param.get("label", param["id"])
            full_label = param.get("full_label", "")
            val = config_data.get(param["id"], "")

            if param.get("type") == "select" and param.get("options"):
                for opt in param["options"]:
                    if str(opt["value"]) == str(val):
                        val = f"{val} ({opt['text']})"
                        break

            fl = full_label[:52] + "…" if len(full_label) > 52 else full_label
            insert_text(page, (col_id + 2, y + 10), label_text, fontsize=7)
            insert_text(page, (col_label + 2, y + 10), fl, fontsize=7)
            insert_text(
                page,
                (col_val + 2, y + 10),
                str(val) if val is not None else "—",
                fontsize=7,
            )

            y += row_h

        y += 4

    # ─── Подпись ─────────────────────────────────────────────────────────────
    if y > 780:
        page = doc.new_page(width=595, height=842)
        if use_custom_font:
            page.insert_font(fontname="dvu", fontfile=FONT_PATH)
        y = 40

    y += 20
    page.draw_line((margin_l, y), (margin_r, y), color=GRAY, width=0.5)
    y += 12

    date_str = datetime.now().strftime("%d.%m.%Y")
    insert_text(page, (margin_l, y), f"Дата: {date_str}", fontsize=9)
    insert_text(page, (margin_r - 150, y), "Подпись: _______________", fontsize=9)
    y += 16
    insert_text(page, (margin_l, y), "Инженер: ___________________________", fontsize=9)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
