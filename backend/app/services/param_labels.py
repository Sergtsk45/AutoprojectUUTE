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


def compute_client_document_missing(
    uploaded_categories: set[str],
    survey_data: dict | None = None,
) -> list[str]:
    """Какие из обязательных документов ещё не загружены.

    Args:
        uploaded_categories: Множество кодов уже загруженных файлов.
        survey_data: Данные опросного листа. Если содержит ``scheme_config``,
            ``heat_scheme`` исключается из missing (будет сгенерирован автоматически).

    Returns:
        Список кодов недостающих документов.
    """
    missing: list[str] = []
    for code in CLIENT_DOCUMENT_PARAM_CODES:
        if code in uploaded_categories:
            continue
        if code == "heat_scheme" and survey_data and "scheme_config" in survey_data:
            continue
        missing.append(code)
    return missing


_LEGACY_DOCUMENT_PARAM_CODES = frozenset(
    {
        "floor_plan",
        "connection_scheme",
        "system_type",
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


def get_missing_items(missing_params: list[str]) -> list[dict[str, str]]:
    """Превращает список machine-name в список для шаблона письма.

    Returns:
        [{"label": "...", "hint": "..."}, ...]

    Все коды ожидаются в каноническом snake_case lowercase (фаза B2.b,
    2026-04-22). Legacy UPPER_CASE-варианты больше не канонизируются —
    исторические данные мигрированы Alembic-ревизией
    `20260421_uute_fc_lower_missing`. Незнакомые коды показываются как
    plain text, без подписи.
    """
    items = []
    for code in missing_params:
        info = MISSING_PARAM_LABELS.get(code)
        if info:
            items.append({"label": info["label"], "hint": info.get("hint", "")})
        else:
            items.append({"label": code, "hint": ""})
    return items


def get_sample_paths(missing_params: list[str]) -> list[str]:
    """Возвращает пути к образцам, релевантным для missing_params.

    Ожидает snake_case lowercase коды (фаза B2.b). Legacy UPPER_CASE
    теперь возвращает пустой список для соответствующего кода.
    """
    return [SAMPLE_DOCUMENTS[code] for code in missing_params if code in SAMPLE_DOCUMENTS]
