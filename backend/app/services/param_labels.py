"""Справочник параметров, запрашиваемых у клиента.

Ключ — machine-name (хранится в order.missing_params).
label — что показываем клиенту в письме.
hint  — подсказка, как подготовить документ.

Коды документов совпадают с `FileCategory.<member>.value` для загружаемых файлов.
После фазы B2 (2026-04-21) все коды — в snake_case lowercase.
"""

# Обязательные документы от клиента после ТУ (фиксированный порядок в UI)
CLIENT_DOCUMENT_PARAM_CODES: tuple[str, ...] = (
    "balance_act",
    "connection_plan",
    "heat_point_plan",
    "heat_scheme",
    "company_card",
)


def compute_client_document_missing(uploaded_categories: set[str]) -> list[str]:
    """Какие из четырёх обязательных документов ещё не загружены."""
    return [c for c in CLIENT_DOCUMENT_PARAM_CODES if c not in uploaded_categories]


_LEGACY_DOCUMENT_PARAM_CODES = frozenset(
    {
        "floor_plan",
        "connection_scheme",
        "system_type",
        # B2 legacy: до 2026-04-21 использовались UPPER_CASE коды
        "BALANCE_ACT",
        "CONNECTION_PLAN",
    }
)


def client_document_list_needs_migration(missing: list[str] | None) -> bool:
    """True, если в missing_params устаревшие или посторонние коды (нужна замена на канонические четыре)."""
    m = missing or []
    allowed = set(CLIENT_DOCUMENT_PARAM_CODES)
    if any(x in _LEGACY_DOCUMENT_PARAM_CODES for x in m):
        return True
    if any(x not in allowed for x in m):
        return True
    return False


MISSING_PARAM_LABELS: dict[str, dict[str, str]] = {
    "tu": {
        "label": "Технические условия",
        "hint": "Документ от теплоснабжающей организации",
    },
    "balance_act": {
        "label": "Акт разграничения балансовой принадлежности",
        "hint": "Для действующих объектов",
    },
    "connection_plan": {
        "label": "План подключения потребителя к тепловой сети",
        "hint": "С указанием точек подключения",
    },
    "heat_point_plan": {
        "label": "План теплового пункта с указанием мест установки узла учёта и ШУ",
        "hint": "",
    },
    "heat_scheme": {
        "label": "Принципиальная схема теплового пункта с узлом учёта",
        "hint": "",
    },
    "company_card": {
        "label": "Карточка предприятия (реквизиты организации)",
        "hint": "PDF или фото с ИНН, КПП, расчётным счётом, БИК и адресом",
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
    "meter_location_photo": {
        "label": "Фото места установки узла учёта",
        "hint": "Общий вид помещения и место предполагаемой установки",
    },
}


# Документы, которые прикладываются как образцы
SAMPLE_DOCUMENTS: dict[str, str] = {
    "balance_act": "samples/sample_balance_act.pdf",
    "connection_plan": "samples/sample_connection_plan.pdf",
    "heat_point_plan": "samples/sample_heat_point_plan.pdf",
    "heat_scheme": "samples/sample_heat_scheme.pdf",
}


# Исторические UPPER_CASE коды → canonical lowercase (B2 compat shim).
# Удалить в B2.b вместе с `FileCategory._missing_`.
_B2_LEGACY_ALIASES: dict[str, str] = {
    "BALANCE_ACT": "balance_act",
    "CONNECTION_PLAN": "connection_plan",
}


def _canonicalize(code: str) -> str:
    return _B2_LEGACY_ALIASES.get(code, code)


def get_missing_items(missing_params: list[str]) -> list[dict[str, str]]:
    """Превращает список machine-name в список для шаблона письма.

    Returns:
        [{"label": "...", "hint": "..."}, ...]
    """
    items = []
    for raw_code in missing_params:
        code = _canonicalize(raw_code)
        info = MISSING_PARAM_LABELS.get(code)
        if info:
            items.append({"label": info["label"], "hint": info.get("hint", "")})
        else:
            # Неизвестный код — показываем как есть
            items.append({"label": raw_code, "hint": ""})
    return items


def get_sample_paths(missing_params: list[str]) -> list[str]:
    """Возвращает пути к образцам, релевантным для missing_params."""
    paths = []
    for raw_code in missing_params:
        code = _canonicalize(raw_code)
        if code in SAMPLE_DOCUMENTS:
            paths.append(SAMPLE_DOCUMENTS[code])
    return paths
