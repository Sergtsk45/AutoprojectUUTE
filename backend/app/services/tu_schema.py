"""Схема параметров, извлекаемых из технических условий.

Определяет:
- Полный перечень параметров по Правилам 1034/1036
- Типы данных и единицы измерения
- Валидационные диапазоны
- Какие параметры обязательны, какие опциональны
"""

from pydantic import BaseModel, Field
from typing import Literal

# Допустимые значения connection.system_type (синхронно с парсером и LLM)
SYSTEM_TYPE_ALLOWED: frozenset[str] = frozenset({
    "закрытая",
    "открытая",
    "закрытая_двухтрубная",
    "закрытая_четырёхтрубная",
    "открытая_двухтрубная",
    "открытая_четырёхтрубная",
    "двухтрубная",
    "четырёхтрубная",
    "неизвестно",
})


class RSOInfo(BaseModel):
    """Данные ресурсоснабжающей организации."""

    rso_name: str | None = Field(None, description="Наименование РСО")
    rso_address: str | None = Field(None, description="Адрес РСО")
    rso_phone: str | None = Field(None, description="Телефон РСО")
    rso_email: str | None = Field(None, description="Email РСО")
    rso_website: str | None = Field(None, description="Сайт РСО")


class TUDocumentInfo(BaseModel):
    """Реквизиты документа ТУ."""

    tu_number: str | None = Field(None, description="Номер ТУ")
    tu_date: str | None = Field(None, description="Дата выдачи ТУ (ДД.ММ.ГГГГ)")
    tu_valid_from: str | None = Field(None, description="Действует с (ДД.ММ.ГГГГ)")
    tu_valid_to: str | None = Field(None, description="Действует по (ДД.ММ.ГГГГ)")
    tu_response_to: str | None = Field(None, description="На основании заявки №... от ...")
    signatory_name: str | None = Field(None, description="ФИО подписанта")
    signatory_position: str | None = Field(None, description="Должность подписанта")


class ApplicantInfo(BaseModel):
    """Данные заявителя (потребителя)."""

    applicant_name: str | None = Field(None, description="Наименование заявителя")
    applicant_address: str | None = Field(None, description="Почтовый адрес заявителя")
    contact_person: str | None = Field(None, description="Контактное лицо")


class ObjectInfo(BaseModel):
    """Данные об объекте."""

    object_type: str | None = Field(
        None,
        description="Тип объекта: МКД, нежилое здание, промышленное и т.д.",
    )
    object_address: str | None = Field(None, description="Адрес объекта теплоснабжения")
    city: str | None = Field(None, description="Город")


class HeatLoads(BaseModel):
    """Тепловые нагрузки (Гкал/ч)."""

    total_load: float | None = Field(
        None, ge=0, le=100, description="Общая договорная тепловая нагрузка, Гкал/ч"
    )
    heating_load: float | None = Field(
        None, ge=0, le=100, description="Отопление, Гкал/ч"
    )
    ventilation_load: float | None = Field(
        None, ge=0, le=100, description="Вентиляция, Гкал/ч"
    )
    hot_water_load: float | None = Field(
        None, ge=0, le=100, description="ГВС, Гкал/ч"
    )


class PipelineParams(BaseModel):
    """Параметры трубопроводов."""

    pipe_outer_diameter_mm: float | None = Field(
        None, ge=15, le=1420, description="Наружный диаметр подающего/обратного, мм"
    )
    pipe_inner_diameter_mm: float | None = Field(
        None, ge=10, le=1400, description="Внутренний (условный) диаметр, мм"
    )


class CoolantParams(BaseModel):
    """Параметры теплоносителя."""

    # Температурный график
    supply_temp: float | None = Field(
        None, ge=50, le=180, description="Температура подачи (макс), °C"
    )
    return_temp: float | None = Field(
        None, ge=30, le=100, description="Температура обратки (макс), °C"
    )
    temp_schedule: str | None = Field(
        None, description="Температурный график, например '150/70' или '117.2/70'"
    )
    heating_season: str | None = Field(
        None, description="Отопительный сезон, например '2024/2025'"
    )

    # Давления
    supply_pressure_kgcm2: float | None = Field(
        None, ge=0, le=25, description="Расчётное давление в подающем, кг/см²"
    )
    return_pressure_kgcm2: float | None = Field(
        None, ge=0, le=25, description="Расчётное давление в обратном, кг/см²"
    )


class MeteringRequirements(BaseModel):
    """Требования к узлу учёта и приборам."""

    meter_location: str | None = Field(
        None, description="Место установки узла учёта (на вводе, в ИТП и т.д.)"
    )
    heat_calculator_model: str | None = Field(
        None, description="Рекомендуемый тепловычислитель"
    )
    flowmeter_model: str | None = Field(
        None, description="Рекомендуемые расходомеры"
    )
    temp_sensor_model: str | None = Field(
        None, description="Рекомендуемые датчики температуры"
    )
    pressure_sensor_model: str | None = Field(
        None, description="Рекомендуемые датчики давления"
    )
    heat_meter_class: int | None = Field(
        None, ge=1, le=4, description="Класс точности теплосчётчика (не ниже)"
    )
    data_interface: str | None = Field(
        None, description="Интерфейс передачи данных (RS-485, GSM модем и т.д.)"
    )
    archive_capacity_hours: int | None = Field(
        None, description="Ёмкость архива часового, суток"
    )
    archive_capacity_daily: int | None = Field(
        None, description="Ёмкость архива суточного, месяцев"
    )
    archive_capacity_monthly: int | None = Field(
        None, description="Ёмкость архива месячного, лет"
    )


class ConnectionScheme(BaseModel):
    """Схема подключения."""

    connection_type: Literal[
        "зависимая", "независимая", "неизвестно"
    ] | None = Field(None, description="Тип присоединения")
    system_type: Literal[
        "закрытая",
        "открытая",
        "закрытая_двухтрубная",
        "закрытая_четырёхтрубная",
        "открытая_двухтрубная",
        "открытая_четырёхтрубная",
        "двухтрубная",
        "четырёхтрубная",
        "неизвестно",
    ] | None = Field(None, description="Тип системы теплоснабжения")
    heating_system: str | None = Field(
        None, description="Система отопления: отопление, ГВС, вентиляция и т.д."
    )


class AdditionalRequirements(BaseModel):
    """Дополнительные требования из ТУ."""

    approval_organization: str | None = Field(
        None, description="Организация для согласования проекта"
    )
    pre_survey_required: bool | None = Field(
        None, description="Требуется акт предпроектного обследования"
    )
    gcs_module: bool | None = Field(
        None, description="Требуется модуль ГСМ для передачи данных"
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Дополнительные примечания и требования из ТУ",
    )


class TUParsedData(BaseModel):
    """Полная структура данных, извлечённых из технических условий.

    Это «мастер-схема» — итог работы парсера.
    Заполняется из PDF через LLM-извлечение.
    """

    rso: RSOInfo = Field(default_factory=RSOInfo)
    document: TUDocumentInfo = Field(default_factory=TUDocumentInfo)
    applicant: ApplicantInfo = Field(default_factory=ApplicantInfo)
    object: ObjectInfo = Field(default_factory=ObjectInfo)
    heat_loads: HeatLoads = Field(default_factory=HeatLoads)
    pipeline: PipelineParams = Field(default_factory=PipelineParams)
    coolant: CoolantParams = Field(default_factory=CoolantParams)
    metering: MeteringRequirements = Field(default_factory=MeteringRequirements)
    connection: ConnectionScheme = Field(default_factory=ConnectionScheme)
    additional: AdditionalRequirements = Field(default_factory=AdditionalRequirements)

    # Метаданные парсинга
    parse_confidence: float = Field(
        0.0, ge=0, le=1, description="Общая уверенность парсера (0–1)"
    )
    raw_text: str = Field("", description="Исходный текст из PDF (для отладки)")
    warnings: list[str] = Field(
        default_factory=list,
        description="Предупреждения парсера (нечитаемые фрагменты, несоответствия)",
    )


# ─── Обязательные параметры (без них нельзя двигать в data_complete) ──────────

REQUIRED_PARSED_FIELDS = [
    "heat_loads.total_load",
    "pipeline.pipe_outer_diameter_mm",
    "coolant.supply_temp",
    "coolant.return_temp",
    "coolant.supply_pressure_kgcm2",
    "coolant.return_pressure_kgcm2",
    "object.object_address",
]

# Параметры, которые нужны, но можно запросить у клиента
REQUESTABLE_FIELDS = [
    "connection.connection_type",
    "connection.system_type",
    "heat_loads.heating_load",
    "heat_loads.hot_water_load",
]


def get_missing_fields(data: TUParsedData) -> list[str]:
    """Возвращает список незаполненных обязательных полей.

    Используется оркестратором для определения — нужно ли
    запрашивать доп. информацию у клиента.
    """
    missing = []

    for dotted_path in REQUIRED_PARSED_FIELDS:
        parts = dotted_path.split(".")
        obj = data
        for part in parts:
            obj = getattr(obj, part, None)
            if obj is None:
                break
        if obj is None:
            missing.append(dotted_path)

    return missing
