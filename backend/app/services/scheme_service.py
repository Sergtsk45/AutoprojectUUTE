"""
@file: scheme_service.py
@description: Маппинг конфигурации принципиальной схемы УУТЭ на тип шаблона и извлечение параметров из parsed_params.
@dependencies: app.schemas.scheme
@created: 2026-04-19
"""

from __future__ import annotations

from typing import Any

from app.schemas.scheme import (
    SchemeConfig,
    SchemeParams,
    SchemeTemplateInfo,
    SchemeType,
)

# Ключ: (connection_type, has_valve, has_gwp, has_ventilation) → тип SVG-шаблона
SCHEME_MAP: dict[tuple[str, bool, bool, bool], SchemeType] = {
    ("dependent", False, False, False): SchemeType.DEP_SIMPLE,
    ("dependent", False, True, False): SchemeType.DEP_SIMPLE_GWP,
    ("dependent", True, False, False): SchemeType.DEP_VALVE,
    ("dependent", True, True, False): SchemeType.DEP_VALVE_GWP,
    ("dependent", True, True, True): SchemeType.DEP_VALVE_GWP_VENT,
    ("independent", True, False, False): SchemeType.INDEP,
    ("independent", True, True, False): SchemeType.INDEP_GWP,
    ("independent", True, True, True): SchemeType.INDEP_GWP_VENT,
}

SCHEME_LABELS: dict[SchemeType, dict[str, str]] = {
    SchemeType.DEP_SIMPLE: {
        "label": "Зависимая, без клапана",
        "description": (
            "Зависимая схема присоединения, без регулирующего клапана, "
            "без ГВС и без вентиляции."
        ),
    },
    SchemeType.DEP_SIMPLE_GWP: {
        "label": "Зависимая, без клапана, с ГВС",
        "description": (
            "Зависимая схема, без регулирующего клапана, "
            "с ГВС (двухступенчатый подогреватель, смешанная схема), без вентиляции."
        ),
    },
    SchemeType.DEP_VALVE: {
        "label": "Зависимая, 3-ходовой клапан и насос",
        "description": (
            "Зависимая схема: 3-ходовой клапан и насос на перемычке, "
            "без ГВС и без вентиляции."
        ),
    },
    SchemeType.DEP_VALVE_GWP: {
        "label": "Зависимая, клапан и насос, с ГВС",
        "description": (
            "Зависимая схема: 3-ходовой клапан и насос на перемычке, с ГВС, без вентиляции."
        ),
    },
    SchemeType.DEP_VALVE_GWP_VENT: {
        "label": "Зависимая, клапан и насос, ГВС и вентиляция",
        "description": (
            "Зависимая схема: 3-ходовой клапан и насос на перемычке, "
            "с ГВС и параллельной вентиляцией."
        ),
    },
    SchemeType.INDEP: {
        "label": "Независимая, клапан, насос, подпитка G3",
        "description": (
            "Независимая схема: 2-ходовой клапан, насос, подпитка G3, "
            "без ГВС и без вентиляции."
        ),
    },
    SchemeType.INDEP_GWP: {
        "label": "Независимая, клапан и подпитка G3, с ГВС",
        "description": (
            "Независимая схема: 2-ходовой клапан, насос, подпитка G3, с ГВС, без вентиляции."
        ),
    },
    SchemeType.INDEP_GWP_VENT: {
        "label": "Независимая, ГВС и вентиляция",
        "description": (
            "Независимая схема: 2-ходовой клапан, насос, подпитка G3, "
            "с ГВС и параллельной вентиляцией."
        ),
    },
}

# Метаданные шаблонов для UI (порядок — с 1 по 8 схему)
_SCHEME_TEMPLATE_ORDER: list[SchemeType] = [
    SchemeType.DEP_SIMPLE,
    SchemeType.DEP_SIMPLE_GWP,
    SchemeType.DEP_VALVE,
    SchemeType.DEP_VALVE_GWP,
    SchemeType.DEP_VALVE_GWP_VENT,
    SchemeType.INDEP,
    SchemeType.INDEP_GWP,
    SchemeType.INDEP_GWP_VENT,
]

_SCHEME_UI_META: dict[SchemeType, tuple[str, bool, bool]] = {
    SchemeType.DEP_SIMPLE: ("dependent", False, False),
    SchemeType.DEP_SIMPLE_GWP: ("dependent", True, False),
    SchemeType.DEP_VALVE: ("dependent", False, False),
    SchemeType.DEP_VALVE_GWP: ("dependent", True, False),
    SchemeType.DEP_VALVE_GWP_VENT: ("dependent", True, True),
    SchemeType.INDEP: ("independent", False, False),
    SchemeType.INDEP_GWP: ("independent", True, False),
    SchemeType.INDEP_GWP_VENT: ("independent", True, True),
}


def resolve_scheme_type(config: SchemeConfig) -> SchemeType | None:
    """Определяет тип схемы по конфигурации. None если комбинация не входит в SCHEME_MAP."""
    key = (
        config.connection_type,
        config.has_valve,
        config.has_gwp,
        config.has_ventilation,
    )
    return SCHEME_MAP.get(key)


def get_available_templates() -> list[SchemeTemplateInfo]:
    """Возвращает список всех доступных шаблонов для UI (8 типовых конфигураций)."""
    result: list[SchemeTemplateInfo] = []
    for st in _SCHEME_TEMPLATE_ORDER:
        meta = SCHEME_LABELS[st]
        conn, has_gwp, has_vent = _SCHEME_UI_META[st]
        result.append(
            SchemeTemplateInfo(
                scheme_type=st,
                label=meta["label"],
                description=meta["description"],
                has_gwp=has_gwp,
                has_ventilation=has_vent,
                connection_type=conn,
            )
        )
    return result


def _get_nested(data: dict[str, Any], path: str) -> Any:
    keys = path.split(".")
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current


def _scalar_to_str(value: Any) -> str | None:
    """Приводит значение из JSON/parsed_params к строке для подстановки в SVG."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    if isinstance(value, int):
        return str(value)
    return str(value)


def _pick(
    parsed: dict[str, Any],
    nested_path: str,
    *flat_keys: str,
) -> Any:
    """Сначала вложенный путь (TUParsedData), затем плоские ключи (legacy)."""
    v = _get_nested(parsed, nested_path)
    if v is not None:
        return v
    for k in flat_keys:
        if k in parsed and parsed[k] is not None:
            return parsed[k]
    return None


def extract_scheme_params_from_parsed(parsed_params: dict | None) -> SchemeParams:
    """Извлекает параметры для SVG из parsed_params заявки.

    Поддерживает вложенную структуру ``TUParsedData`` и частично плоский legacy-формат
    (поля на верхнем уровне или в том же виде, что ключи опроса на фронте).
    """
    p: dict[str, Any] = parsed_params if isinstance(parsed_params, dict) else {}

    pipe = _scalar_to_str(
        _pick(
            p,
            "pipeline.pipe_outer_diameter_mm",
            "pipe_outer_diameter_mm",
            "pipe_dn_supply",
        )
    )
    t1 = _scalar_to_str(
        _pick(p, "coolant.supply_temp", "supply_temp")
    )
    t2 = _scalar_to_str(
        _pick(p, "coolant.return_temp", "return_temp")
    )
    pr_sup = _scalar_to_str(
        _pick(
            p,
            "coolant.supply_pressure_kgcm2",
            "supply_pressure_kgcm2",
            "pressure_supply",
        )
    )
    pr_ret = _scalar_to_str(
        _pick(
            p,
            "coolant.return_pressure_kgcm2",
            "return_pressure_kgcm2",
            "pressure_return",
        )
    )

    hl_block = p.get("heat_loads")
    hl_heating = None
    hl_hw = None
    hl_vent = None
    hl_total = None
    if isinstance(hl_block, dict):
        hl_heating = hl_block.get("heating_load")
        hl_hw = hl_block.get("hot_water_load")
        hl_vent = hl_block.get("ventilation_load")
        hl_total = hl_block.get("total_load")

    heating = _scalar_to_str(
        hl_heating
        if hl_heating is not None
        else _pick(p, "heat_loads.heating_load", "heating_load", "heat_load_heating")
    )
    gwp = _scalar_to_str(
        hl_hw
        if hl_hw is not None
        else _pick(
            p,
            "heat_loads.hot_water_load",
            "hot_water_load",
            "heat_load_hw",
        )
    )
    vent = _scalar_to_str(
        hl_vent
        if hl_vent is not None
        else _pick(
            p,
            "heat_loads.ventilation_load",
            "ventilation_load",
            "heat_load_vent",
        )
    )
    total = _scalar_to_str(
        hl_total
        if hl_total is not None
        else _pick(p, "heat_loads.total_load", "total_load", "heat_load_total")
    )

    tu_num = _scalar_to_str(
        _pick(p, "document.tu_number", "tu_number", "project_number")
    )
    addr = _scalar_to_str(
        _pick(p, "object.object_address", "object_address", "address")
    )
    company = _scalar_to_str(
        _pick(
            p,
            "applicant.applicant_name",
            "applicant_name",
            "company_name",
            "client_organization",
        )
    )
    engineer = _scalar_to_str(
        _pick(
            p,
            "applicant.contact_person",
            "contact_person",
            "document.signatory_name",
            "signatory_name",
            "engineer_name",
        )
    )

    return SchemeParams(
        pipe_diameter=pipe,
        supply_temp=t1,
        return_temp=t2,
        supply_pressure=pr_sup,
        return_pressure=pr_ret,
        heating_load=heating,
        gwp_load=gwp,
        ventilation_load=vent,
        total_load=total,
        project_number=tu_num,
        object_address=addr,
        company_name=company,
        engineer_name=engineer,
    )
