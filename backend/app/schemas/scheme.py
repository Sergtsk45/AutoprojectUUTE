"""
@file: scheme.py
@description: Pydantic-схемы конфигурации принципиальной схемы теплового пункта и генерации SVG.
@dependencies: pydantic
@created: 2026-04-19
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SchemeType(str, Enum):
    """Тип конфигурации схемы — machine-name для маппинга на SVG."""

    DEP_SIMPLE = "dep_simple"  # Схема 1
    DEP_SIMPLE_GWP = "dep_simple_gwp"  # Схема 2
    DEP_VALVE = "dep_valve"  # Схема 3
    DEP_VALVE_GWP = "dep_valve_gwp"  # Схема 4
    DEP_VALVE_GWP_VENT = "dep_valve_gwp_vent"  # Схема 5
    INDEP = "indep"  # Схема 6
    INDEP_GWP = "indep_gwp"  # Схема 7
    INDEP_GWP_VENT = "indep_gwp_vent"  # Схема 8


class SchemeConfig(BaseModel):
    """Конфигурация, выбранная клиентом через UI."""

    connection_type: Literal["dependent", "independent"]
    has_valve: bool = Field(
        default=False,
        description="Регулирующий клапан (3-ходовой в зависимой, 2-ходовой в независимой схеме).",
    )
    has_gwp: bool = Field(default=False, description="Наличие контура ГВС.")
    has_ventilation: bool = Field(
        default=False,
        description="Наличие параллельной вентиляции (только в допустимых сочетаниях с ГВС).",
    )

    @model_validator(mode="after")
    def validate_scheme_combination(self) -> SchemeConfig:
        """Проверяет допустимость сочетания признаков для одной из 8 типовых схем."""
        if self.connection_type == "independent":
            if not self.has_valve:
                raise ValueError(
                    "Для независимой схемы обязательны 2-ходовой клапан и насос "
                    "(has_valve должен быть True)."
                )
            if self.has_ventilation and not self.has_gwp:
                raise ValueError(
                    "Вентиляция в независимой схеме допустима только при наличии ГВС."
                )
        if self.connection_type == "dependent":
            if self.has_ventilation:
                if not self.has_gwp:
                    raise ValueError(
                        "Вентиляция в зависимой схеме предусмотрена только вместе с ГВС."
                    )
                if not self.has_valve:
                    raise ValueError(
                        "Вентиляция в зависимой схеме — только при регулировании "
                        "3-ходовым клапаном (has_valve должен быть True)."
                    )
        return self


class SchemeParams(BaseModel):
    """Параметры для подстановки в SVG-шаблон (из parsed_params заявки)."""

    pipe_diameter: str | None = None
    supply_temp: str | None = None
    return_temp: str | None = None
    supply_pressure: str | None = None
    return_pressure: str | None = None
    heating_load: str | None = None
    gwp_load: str | None = None
    ventilation_load: str | None = None
    total_load: str | None = None
    project_number: str | None = None
    object_address: str | None = None
    company_name: str | None = None
    engineer_name: str | None = None


class SchemeGenerateRequest(BaseModel):
    """Запрос на генерацию схемы."""

    config: SchemeConfig
    params: SchemeParams | None = None


class SchemePreviewResponse(BaseModel):
    """Ответ с превью SVG."""

    scheme_type: SchemeType
    scheme_label: str
    svg_content: str


class SchemeTemplateInfo(BaseModel):
    """Информация о доступном шаблоне для UI."""

    scheme_type: SchemeType
    label: str
    description: str
    has_gwp: bool
    has_ventilation: bool
    connection_type: str
