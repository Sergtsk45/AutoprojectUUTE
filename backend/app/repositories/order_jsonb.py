"""
@file: app/repositories/order_jsonb.py
@description: Типизированные accessor-методы для JSONB-полей модели `Order`.
    Фаза B1 аудита раздела 3. Валидация происходит при чтении (а не при записи
    LLM-результата) — исторические записи с устаревшими ключами не роняют код,
    вместо этого логируется WARNING и возвращается `None` (или
    `SurveyData(**{})` для опроса).

    Ключевая идея: бизнес-код больше НЕ должен обращаться к
    `order.parsed_params["heat_loads"]["heating_load"]` — только через
    `get_parsed_params(order)` → типизированная модель.

@dependencies:
    - app.models.models.Order
    - app.schemas.jsonb.* (Pydantic-модели)
@created: 2026-04-21
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import TypeAdapter, ValidationError

from app.schemas.jsonb.company import CompanyRequisites
from app.schemas.jsonb.survey import SurveyData
from app.schemas.jsonb.tu import TUParsedData

if TYPE_CHECKING:  # pragma: no cover — только для тайп-чекера
    from app.models.models import Order

logger = logging.getLogger(__name__)


# TypeAdapter-ы создаём один раз на модуль — они кэшируют сгенерированную
# валидационную схему и переиспользуются между вызовами.
_TU_ADAPTER: TypeAdapter[TUParsedData] = TypeAdapter(TUParsedData)
_SURVEY_ADAPTER: TypeAdapter[SurveyData] = TypeAdapter(SurveyData)
_COMPANY_ADAPTER: TypeAdapter[CompanyRequisites] = TypeAdapter(CompanyRequisites)


# ─── parsed_params ────────────────────────────────────────────────────────────


def get_parsed_params(order: Order) -> TUParsedData | None:
    """Типизированное чтение `order.parsed_params`.

    Возвращает `None`, если поле не заполнено или содержит невалидные данные
    (в этом случае логируется WARNING — см. ниже). Вызывающий код должен быть
    готов к `None` и не ломаться.
    """
    raw = order.parsed_params
    if not raw:
        return None
    try:
        return _TU_ADAPTER.validate_python(raw)
    except ValidationError as exc:
        logger.warning(
            "parsed_params невалидны для заявки %s: %s",
            order.id,
            _summarize_errors(exc),
        )
        return None


def set_parsed_params(order: Order, data: TUParsedData | None) -> None:
    """Сохраняет `TUParsedData` в JSONB-поле (или `None`, чтобы очистить).

    Использует `mode="json"` чтобы корректно сериализовать datetime, Decimal и др.
    """
    order.parsed_params = data.model_dump(mode="json") if data is not None else None


# ─── survey_data ──────────────────────────────────────────────────────────────


def get_survey_data(order: Order) -> SurveyData | None:
    """Типизированное чтение `order.survey_data`.

    Для custom-заказов возвращает `SurveyData`, для express/неизвестных —
    возможно `None`. На невалидных данных — WARNING и `None`.
    """
    raw = order.survey_data
    if not raw:
        return None
    try:
        return _SURVEY_ADAPTER.validate_python(raw)
    except ValidationError as exc:
        logger.warning(
            "survey_data невалидны для заявки %s: %s",
            order.id,
            _summarize_errors(exc),
        )
        return None


def set_survey_data(order: Order, data: SurveyData | None) -> None:
    """Сохраняет `SurveyData` в JSONB-поле."""
    order.survey_data = data.model_dump(mode="json") if data is not None else None


# ─── company_requisites ───────────────────────────────────────────────────────


def get_company_requisites(order: Order) -> CompanyRequisites | None:
    """Типизированное чтение `order.company_requisites`.

    Записи, где поле содержит ключ `error` (маркер неудачного парсинга),
    валидируются штатно — `CompanyRequisites` с `extra="ignore"` просто
    проигнорирует этот ключ, а вызывающий код должен отдельно проверить
    `requisitesReady(...)` (фронт) или `order.company_requisites.get("error")`.

    Возвращает `None`, если поле пустое или невалидное.
    """
    raw = order.company_requisites
    if not raw:
        return None
    try:
        return _COMPANY_ADAPTER.validate_python(raw)
    except ValidationError as exc:
        logger.warning(
            "company_requisites невалидны для заявки %s: %s",
            order.id,
            _summarize_errors(exc),
        )
        return None


def set_company_requisites(order: Order, data: CompanyRequisites | None) -> None:
    """Сохраняет `CompanyRequisites` в JSONB-поле."""
    order.company_requisites = data.model_dump(mode="json") if data is not None else None


# ─── helpers ──────────────────────────────────────────────────────────────────


def _summarize_errors(exc: ValidationError, limit: int = 3) -> str:
    """Короткая сводка ошибок валидации для лога (первые `limit` ошибок)."""
    errors = exc.errors()
    summary: list[str] = []
    for err in errors[:limit]:
        loc = ".".join(str(p) for p in err.get("loc", ()))
        msg = err.get("msg", "")
        summary.append(f"{loc}: {msg}")
    if len(errors) > limit:
        summary.append(f"...+{len(errors) - limit} more")
    return "; ".join(summary)
