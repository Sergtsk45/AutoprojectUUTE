"""
@file: app/schemas/jsonb/__init__.py
@description: Pydantic-модели для JSONB-полей таблицы `orders`.
    Фаза B1 аудита — типизация `parsed_params`, `survey_data`, `company_requisites`.
    Данные валидируются в accessor-методах `app.repositories.order_jsonb` при чтении
    (extra='ignore' + log WARNING), а не при записи LLM-результата.
@dependencies: pydantic v2.
@created: 2026-04-21
"""

from app.schemas.jsonb.company import CompanyRequisites, CompanyRequisitesError
from app.schemas.jsonb.survey import SurveyData
from app.schemas.jsonb.tu import (
    AdditionalRequirements,
    ApplicantInfo,
    ConnectionScheme,
    CoolantParams,
    HeatLoads,
    MeteringRequirements,
    ObjectInfo,
    PipelineParams,
    RSOInfo,
    SYSTEM_TYPE_ALLOWED,
    TUDocumentInfo,
    TUParsedData,
    REQUESTABLE_FIELDS,
    REQUIRED_PARSED_FIELDS,
    get_missing_fields,
)

__all__ = [
    # tu
    "AdditionalRequirements",
    "ApplicantInfo",
    "ConnectionScheme",
    "CoolantParams",
    "HeatLoads",
    "MeteringRequirements",
    "ObjectInfo",
    "PipelineParams",
    "RSOInfo",
    "SYSTEM_TYPE_ALLOWED",
    "TUDocumentInfo",
    "TUParsedData",
    "REQUESTABLE_FIELDS",
    "REQUIRED_PARSED_FIELDS",
    "get_missing_fields",
    # survey
    "SurveyData",
    # company
    "CompanyRequisites",
    "CompanyRequisitesError",
]
