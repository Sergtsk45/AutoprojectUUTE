"""
@file: tests/test_jsonb_schemas.py
@description: Тесты Pydantic-моделей JSONB (`app.schemas.jsonb.*`) и accessor-методов
    репозитория (`app.repositories.order_jsonb`). Фаза B1 аудита.
@created: 2026-04-21
"""

import logging
import unittest
import uuid
from types import SimpleNamespace

from pydantic import ValidationError

from app.repositories.order_jsonb import (
    get_company_requisites,
    get_parsed_params,
    get_survey_data,
    set_company_requisites,
    set_parsed_params,
    set_survey_data,
)
from app.schemas.jsonb import (
    CompanyRequisites,
    SurveyData,
    TUParsedData,
    get_missing_fields,
)


def _fake_order(**fields) -> SimpleNamespace:
    """Мок ORM-объекта Order: используем SimpleNamespace — accessor-ам достаточно
    читать/писать атрибуты `parsed_params`, `survey_data`, `company_requisites`, `id`.
    """
    base = dict(
        id=uuid.uuid4(),
        parsed_params=None,
        survey_data=None,
        company_requisites=None,
    )
    base.update(fields)
    return SimpleNamespace(**base)


# ─── TUParsedData ─────────────────────────────────────────────────────────────


class TUParsedDataTests(unittest.TestCase):
    def test_default_empty_model_is_valid(self) -> None:
        """TUParsedData() работает с дефолтами — важно для LLM-fallback."""
        data = TUParsedData()
        self.assertEqual(data.parse_confidence, 0.0)
        self.assertEqual(data.warnings, [])
        self.assertIsNone(data.heat_loads.total_load)

    def test_validates_nested_fields(self) -> None:
        data = TUParsedData.model_validate(
            {
                "heat_loads": {"total_load": 0.6, "heating_load": 0.45},
                "object": {"object_address": "ул. Ленина 1"},
                "parse_confidence": 0.9,
            }
        )
        self.assertEqual(data.heat_loads.total_load, 0.6)
        self.assertEqual(data.object.object_address, "ул. Ленина 1")
        self.assertEqual(data.parse_confidence, 0.9)

    def test_rejects_out_of_range_values(self) -> None:
        with self.assertRaises(ValidationError):
            TUParsedData.model_validate({"heat_loads": {"total_load": 999.0}})

    def test_extra_keys_ignored(self) -> None:
        """Исторические записи с устаревшими ключами — не должны ломать чтение."""
        data = TUParsedData.model_validate(
            {
                "heat_loads": {"total_load": 0.5, "deprecated_key": "old"},
                "some_removed_section": {"x": 1},
            }
        )
        self.assertEqual(data.heat_loads.total_load, 0.5)

    def test_connection_scheme_literal_validated(self) -> None:
        with self.assertRaises(ValidationError):
            TUParsedData.model_validate({"connection": {"connection_type": "ерунда"}})

    def test_get_missing_fields_reports_absent(self) -> None:
        data = TUParsedData()
        missing = get_missing_fields(data)
        self.assertIn("heat_loads.total_load", missing)
        self.assertIn("object.object_address", missing)

    def test_get_missing_fields_empty_when_all_filled(self) -> None:
        data = TUParsedData.model_validate(
            {
                "heat_loads": {"total_load": 0.5},
                "pipeline": {"pipe_outer_diameter_mm": 100},
                "coolant": {
                    "supply_temp": 110,
                    "return_temp": 70,
                    "supply_pressure_kgcm2": 6.0,
                    "return_pressure_kgcm2": 4.0,
                },
                "object": {"object_address": "ул. Ленина 1"},
            }
        )
        self.assertEqual(get_missing_fields(data), [])


# ─── SurveyData ───────────────────────────────────────────────────────────────


class SurveyDataTests(unittest.TestCase):
    def test_empty_survey_accepted_for_draft_saving(self) -> None:
        """Пустой опрос валиден — фронт сохраняет черновик по ходу заполнения."""
        data = SurveyData()
        self.assertIsNone(data.building_type)
        self.assertIsNone(data.manufacturer)

    def test_manufacturer_literal_enforced(self) -> None:
        with self.assertRaises(ValidationError):
            SurveyData.model_validate({"manufacturer": "UNKNOWN_VENDOR"})

    def test_valid_full_survey(self) -> None:
        data = SurveyData.model_validate(
            {
                "building_type": "жилое",
                "floors": 9,
                "construction_year": 1985,
                "city": "Москва",
                "supply_temp": 130,
                "return_temp": 70,
                "manufacturer": "teplovizor",
                "manufacturer_other": None,
                "has_mud_separators": "yes",
                "has_filters": "no",
            }
        )
        self.assertEqual(data.manufacturer, "teplovizor")
        self.assertEqual(data.has_mud_separators, "yes")

    def test_extra_keys_ignored(self) -> None:
        data = SurveyData.model_validate({"city": "Тула", "future_field": 42})
        self.assertEqual(data.city, "Тула")


# ─── CompanyRequisites ────────────────────────────────────────────────────────


class CompanyRequisitesTests(unittest.TestCase):
    def test_defaults(self) -> None:
        r = CompanyRequisites()
        self.assertEqual(r.full_name, "")
        self.assertEqual(r.director_position, "Генеральный директор")
        self.assertEqual(r.warnings, [])

    def test_model_validate_full(self) -> None:
        r = CompanyRequisites.model_validate(
            {
                "full_name": "ООО «Теплосеть»",
                "inn": "7701234567",
                "kpp": "770101001",
                "bik": "044525225",
                "settlement_account": "40702810900000000001",
                "corr_account": "30101810400000000225",
                "bank_name": "Сбер",
                "legal_address": "Москва",
                "director_name": "Иванов И.И.",
                "parse_confidence": 0.95,
            }
        )
        self.assertEqual(r.inn, "7701234567")
        self.assertEqual(r.parse_confidence, 0.95)

    def test_extra_error_key_from_parser_ignored(self) -> None:
        """Если парсер сохранил {'error': '...'} в company_requisites — чтение должно
        работать (вернётся модель с дефолтами, поле `error` — игнорируется)."""
        r = CompanyRequisites.model_validate({"error": "Не удалось распознать"})
        self.assertEqual(r.full_name, "")


# ─── Accessor-методы (order_jsonb) ────────────────────────────────────────────


class OrderJsonbAccessorsTests(unittest.TestCase):
    def test_get_parsed_params_none_when_empty(self) -> None:
        order = _fake_order(parsed_params=None)
        self.assertIsNone(get_parsed_params(order))
        order2 = _fake_order(parsed_params={})
        self.assertIsNone(get_parsed_params(order2))

    def test_get_parsed_params_valid_roundtrip(self) -> None:
        order = _fake_order()
        set_parsed_params(
            order,
            TUParsedData.model_validate(
                {"heat_loads": {"total_load": 0.7}, "parse_confidence": 0.8}
            ),
        )
        parsed = get_parsed_params(order)
        assert parsed is not None  # mypy hint
        self.assertEqual(parsed.heat_loads.total_load, 0.7)
        self.assertEqual(parsed.parse_confidence, 0.8)

    def test_get_parsed_params_invalid_returns_none_and_warns(self) -> None:
        """Невалидные исторические данные не должны ронять админку — только WARNING."""
        order = _fake_order(parsed_params={"heat_loads": {"total_load": "not-a-number"}})
        with self.assertLogs("app.repositories.order_jsonb", level="WARNING") as cm:
            result = get_parsed_params(order)
        self.assertIsNone(result)
        self.assertTrue(any("parsed_params невалидны" in line for line in cm.output))

    def test_set_parsed_params_none_clears_field(self) -> None:
        order = _fake_order(parsed_params={"heat_loads": {"total_load": 0.5}})
        set_parsed_params(order, None)
        self.assertIsNone(order.parsed_params)

    def test_get_survey_data_handles_partial(self) -> None:
        order = _fake_order(survey_data={"city": "Тула", "manufacturer": "vzlyot"})
        sd = get_survey_data(order)
        assert sd is not None
        self.assertEqual(sd.city, "Тула")
        self.assertEqual(sd.manufacturer, "vzlyot")

    def test_set_survey_data_dumps_json_mode(self) -> None:
        order = _fake_order()
        set_survey_data(order, SurveyData(city="СПб", floors=5))
        self.assertEqual(order.survey_data["city"], "СПб")
        self.assertEqual(order.survey_data["floors"], 5)

    def test_get_company_requisites_tolerates_error_key(self) -> None:
        order = _fake_order(company_requisites={"error": "bad ocr"})
        r = get_company_requisites(order)
        assert r is not None
        self.assertEqual(r.full_name, "")

    def test_set_company_requisites_roundtrip(self) -> None:
        order = _fake_order()
        set_company_requisites(
            order,
            CompanyRequisites(full_name="ООО «Теплосеть»", inn="7701234567"),
        )
        r = get_company_requisites(order)
        assert r is not None
        self.assertEqual(r.inn, "7701234567")

    def test_backward_compat_imports(self) -> None:
        """Старые импорты продолжают работать после переноса."""
        from app.services.tu_schema import TUParsedData as LegacyTU
        from app.services.company_parser import CompanyRequisites as LegacyCR

        self.assertIs(LegacyTU, TUParsedData)
        self.assertIs(LegacyCR, CompanyRequisites)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.WARNING)
    unittest.main()
