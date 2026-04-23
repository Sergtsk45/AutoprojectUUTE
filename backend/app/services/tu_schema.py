"""
@file: app/services/tu_schema.py
@description: Backward-compat shim. Каноническое место моделей ТУ — `app.schemas.jsonb.tu`
    (перенесено в фазе B1 аудита). Все существующие импорты продолжают работать;
    новые импорты следует делать из `app.schemas.jsonb`.
@dependencies: app.schemas.jsonb.tu
@deprecated: 2026-04-21 — убрать после того, как все места перейдут на новый импорт.
"""

from app.schemas.jsonb.tu import (
    AdditionalRequirements,
    ApplicantInfo,
    ConnectionScheme,
    CoolantParams,
    HeatLoads,
    MeteringRequirements,
    ObjectInfo,
    PipelineParams,
    REQUESTABLE_FIELDS,
    REQUIRED_PARSED_FIELDS,
    RSOInfo,
    SYSTEM_TYPE_ALLOWED,
    TUDocumentInfo,
    TUParsedData,
    get_missing_fields,
)

__all__ = [
    "AdditionalRequirements",
    "ApplicantInfo",
    "ConnectionScheme",
    "CoolantParams",
    "HeatLoads",
    "MeteringRequirements",
    "ObjectInfo",
    "PipelineParams",
    "REQUESTABLE_FIELDS",
    "REQUIRED_PARSED_FIELDS",
    "RSOInfo",
    "SYSTEM_TYPE_ALLOWED",
    "TUDocumentInfo",
    "TUParsedData",
    "get_missing_fields",
]
