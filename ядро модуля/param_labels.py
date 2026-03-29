"""Справочник параметров, запрашиваемых у клиента.

Ключ — machine-name (хранится в order.missing_params).
label — что показываем клиенту в письме.
hint  — подсказка, как подготовить документ.
"""

MISSING_PARAM_LABELS: dict[str, dict[str, str]] = {
    "floor_plan": {
        "label": "План помещения с указанием расположения узла учёта и шкафа управления",
        "hint": "Поэтажный план или экспликация с привязкой к осям здания",
    },
    "heat_point_plan": {
        "label": "План теплового пункта",
        "hint": "С указанием расположения оборудования и точек подключения",
    },
    "heat_scheme": {
        "label": "Схема теплоснабжения объекта",
        "hint": "Принципиальная схема с обозначением контуров (отопление, ГВС, вентиляция)",
    },
    "pipe_diameters": {
        "label": "Диаметры трубопроводов на вводе",
        "hint": "Если отличаются от указанных в ТУ",
    },
    "heat_load_details": {
        "label": "Детализация тепловых нагрузок",
        "hint": "С разбивкой по системам: отопление, вентиляция, ГВС",
    },
    "coolant_params": {
        "label": "Параметры теплоносителя",
        "hint": "Температурный график, давление в подающем и обратном трубопроводе",
    },
    "connection_scheme": {
        "label": "Схема присоединения (зависимая/независимая)",
        "hint": "Если не указана в технических условиях",
    },
    "system_type": {
        "label": "Тип системы теплоснабжения (открытая/закрытая)",
        "hint": "Если не указан в технических условиях",
    },
    "meter_location_photo": {
        "label": "Фото места установки узла учёта",
        "hint": "Общий вид помещения и место предполагаемой установки",
    },
}


# Документы, которые прикладываются как образцы
SAMPLE_DOCUMENTS: dict[str, str] = {
    "floor_plan": "samples/sample_floor_plan.pdf",
    "heat_point_plan": "samples/sample_heat_point_plan.pdf",
    "heat_scheme": "samples/sample_heat_scheme.pdf",
}


def get_missing_items(missing_params: list[str]) -> list[dict[str, str]]:
    """Превращает список machine-name в список для шаблона письма.

    Returns:
        [{"label": "...", "hint": "..."}, ...]
    """
    items = []
    for code in missing_params:
        info = MISSING_PARAM_LABELS.get(code)
        if info:
            items.append({"label": info["label"], "hint": info.get("hint", "")})
        else:
            # Неизвестный код — показываем как есть
            items.append({"label": code, "hint": ""})
    return items


def get_sample_paths(missing_params: list[str]) -> list[str]:
    """Возвращает пути к образцам, релевантным для missing_params."""
    paths = []
    for code in missing_params:
        if code in SAMPLE_DOCUMENTS:
            paths.append(SAMPLE_DOCUMENTS[code])
    return paths
