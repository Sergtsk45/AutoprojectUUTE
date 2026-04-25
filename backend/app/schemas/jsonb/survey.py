"""
@file: app/schemas/jsonb/survey.py
@description: Pydantic-модель для `Order.survey_data` — опросный лист клиента,
    заполняется в `backend/static/upload.html` (функция `collectSurveyData`),
    используется в `calculator_config_service` для маппинга в конфиг вычислителя.
@dependencies: pydantic v2.
@created: 2026-04-21
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Да/нет — фиксированные значения select на upload.html.
# Производитель (`manufacturer`) — произвольная строка: значения option в UI менялись
# (esko, teplokom, logika, pulsar, other), а старый Literal ломал сохранение опроса.
YesNo = Literal["yes", "no"]


class SurveyData(BaseModel):
    """Опросный лист клиента для custom-заказов.

    Ключи синхронизированы с `collectSurveyData()` в `backend/static/upload.html`.
    Все поля опциональные: UI валидирует обязательные поля на клиенте; бэкенд
    принимает частично заполненный опрос (для сохранения черновика).
    """

    model_config = ConfigDict(extra="ignore")

    # ── Объект ────────────────────────────────────────────────────────────────
    building_type: str | None = Field(None, description="Тип здания (жилое/нежилое/…)")
    floors: int | None = Field(None, ge=0, le=200, description="Этажность")
    construction_year: int | None = Field(None, ge=1800, le=2100, description="Год постройки")
    city: str | None = Field(None, description="Город")

    # ── Теплоснабжение ────────────────────────────────────────────────────────
    heat_supply_source: str | None = Field(
        None, description="Источник теплоснабжения (ТЭЦ, котельная, …)"
    )
    connection_type: str | None = Field(None, description="Тип присоединения")
    system_type: str | None = Field(None, description="Тип системы теплоснабжения")

    # ── Температуры и давления ────────────────────────────────────────────────
    supply_temp: float | None = Field(None, ge=0, le=200, description="Температура подачи, °C")
    return_temp: float | None = Field(None, ge=0, le=150, description="Температура обратки, °C")
    pressure_supply: float | None = Field(
        None, ge=0, le=30, description="Давление в подающем, кг/см²"
    )
    pressure_return: float | None = Field(
        None, ge=0, le=30, description="Давление в обратном, кг/см²"
    )

    # ── Тепловые нагрузки ─────────────────────────────────────────────────────
    heat_load_total: float | None = Field(
        None, ge=0, le=100, description="Общая тепловая нагрузка, Гкал/ч"
    )
    heat_load_heating: float | None = Field(None, ge=0, le=100, description="Отопление, Гкал/ч")
    heat_load_hw: float | None = Field(None, ge=0, le=100, description="ГВС, Гкал/ч")
    heat_load_vent: float | None = Field(None, ge=0, le=100, description="Вентиляция, Гкал/ч")
    heat_load_tech: float | None = Field(None, ge=0, le=100, description="Технологические, Гкал/ч")

    # ── Трубопроводы ──────────────────────────────────────────────────────────
    pipe_dn_supply: int | None = Field(None, ge=10, le=1500, description="DN подающего, мм")
    pipe_dn_return: int | None = Field(None, ge=10, le=1500, description="DN обратного, мм")

    # ── Оборудование узла учёта ───────────────────────────────────────────────
    has_mud_separators: YesNo | None = Field(None, description="Есть грязевики")
    has_filters: YesNo | None = Field(None, description="Есть фильтры")
    manufacturer: str | None = Field(
        None, description="Производитель тепловычислителя (код из select upload.html)"
    )
    manufacturer_other: str | None = Field(
        None, description="Производитель (если manufacturer='other')"
    )
    flow_meter_type: str | None = Field(
        None, description="Тип расходомера (электромагнитный/ультразвуковой/…)"
    )
    accuracy_class: str | None = Field(None, description="Класс точности")
    meter_location: str | None = Field(None, description="Место установки узла учёта")
    distance_to_vru: float | None = Field(None, ge=0, le=100000, description="Расстояние до ВРУ, м")

    # ── Опциональные маркеры (используются шаблонами калькулятора) ────────────
    # `tcw` — tepovichicel configuration workaround для spt941/tv7/esko_terra
    # (см. `calculator_config_service.auto_fill` и `calculator_templates/*.json`).
    tcw: str | None = Field(None, description="Код конфигурации (устаревший ключ)")

    # ── Свободные текстовые поля ──────────────────────────────────────────────
    rso_requirements: str | None = Field(None, description="Требования РСО")
    comments: str | None = Field(None, description="Комментарии клиента")
