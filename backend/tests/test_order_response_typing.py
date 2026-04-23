"""Тесты строгой типизации `OrderResponse` (фаза B1.c аудита, 2026-04-22).

Проверяем:
- `parsed_params`, `survey_data`, `company_requisites` в `OrderResponse` и
  публичных DTO (`UploadPageInfo`, `PaymentPageInfo`) — типизированные
  Pydantic-модели из `app.schemas.jsonb`, а не `dict`.
- `build_order_response` не падает на «грязных» JSONB — accessor'ы
  `app.repositories.order_jsonb.*` логируют WARNING и возвращают `None`.
- Маркер ошибки парсинга карточки (`{"error": "..."}`) сохраняется в ответе
  как `CompanyRequisitesError`, чтобы фронт `payment.html`/`admin.html`
  продолжал показывать баннер ошибки.
- JSON-сериализация ответа содержит ожидаемые ключи (не теряет `error`).
"""

from __future__ import annotations

import logging
import types
import unittest
import uuid
from datetime import datetime, timezone

from app.models.models import OrderStatus, OrderType
from app.schemas import (
    CompanyRequisitesResponse,
    OrderResponse,
    UploadPageInfo,
    build_order_response,
    company_requisites_for_response,
)
from app.schemas.jsonb import CompanyRequisites, CompanyRequisitesError, SurveyData, TUParsedData


def _mock_order(
    *,
    parsed_params: dict | None = None,
    survey_data: dict | None = None,
    company_requisites: dict | None = None,
    missing_params: list[str] | None = None,
    status: OrderStatus = OrderStatus.NEW,
    order_type: OrderType = OrderType.EXPRESS,
) -> types.SimpleNamespace:
    """Минимальный Order-like объект для тестов `build_order_response`."""
    now = datetime.now(timezone.utc)
    return types.SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        order_type=order_type,
        client_name="Иванов И.И.",
        client_email="ivanov@example.ru",
        client_phone=None,
        client_organization=None,
        object_address=None,
        object_city=None,
        parsed_params=parsed_params,
        missing_params=missing_params,
        survey_data=survey_data,
        retry_count=0,
        reviewer_comment=None,
        payment_method=None,
        payment_amount=None,
        advance_amount=None,
        advance_paid_at=None,
        final_paid_at=None,
        rso_scan_received_at=None,
        company_requisites=company_requisites,
        contract_number=None,
        created_at=now,
        updated_at=now,
        files=[],
        emails=[],
        waiting_client_info_at=None,
    )


class OrderResponseTypingTests(unittest.TestCase):
    def test_fields_are_typed_models(self) -> None:
        """Annotations в OrderResponse — Pydantic-модели, а не `dict`."""
        annotations = OrderResponse.__annotations__
        self.assertIn("TUParsedData", str(annotations["parsed_params"]))
        self.assertIn("SurveyData", str(annotations["survey_data"]))
        self.assertIn("CompanyRequisites", str(annotations["company_requisites"]))
        # `missing_params` сознательно оставлено `list[str]` — в БД бывают legacy-коды.
        self.assertEqual(str(annotations["missing_params"]), "list[str] | None")

    def test_build_order_response_typed_happy_path(self) -> None:
        order = _mock_order(
            parsed_params={
                "rso": {"rso_name": "ПАО Теплосеть"},
                "object": {"object_address": "г. Москва"},
            },
            survey_data={"building_type": "жилое", "floors": 5},
            company_requisites={
                "full_name": "ООО Теплосеть",
                "inn": "7712345678",
                "bik": "044525225",
                "settlement_account": "40702810900000000001",
            },
            order_type=OrderType.CUSTOM,
        )
        resp = build_order_response(order)

        self.assertIsInstance(resp.parsed_params, TUParsedData)
        assert resp.parsed_params is not None  # noqa: S101 — помощь mypy
        self.assertEqual(resp.parsed_params.rso.rso_name, "ПАО Теплосеть")

        self.assertIsInstance(resp.survey_data, SurveyData)
        assert resp.survey_data is not None  # noqa: S101
        self.assertEqual(resp.survey_data.floors, 5)

        self.assertIsInstance(resp.company_requisites, CompanyRequisites)

    def test_build_order_response_error_marker_preserved(self) -> None:
        """`{"error": "..."}` становится `CompanyRequisitesError`."""
        order = _mock_order(company_requisites={"error": "PDF не читаем"})
        resp = build_order_response(order)

        self.assertIsInstance(resp.company_requisites, CompanyRequisitesError)
        assert isinstance(resp.company_requisites, CompanyRequisitesError)  # noqa: S101
        self.assertEqual(resp.company_requisites.error, "PDF не читаем")

        dumped = resp.model_dump(mode="json")
        # Фронт `payment.html` и `admin.html` проверяют `data.company_requisites.error`.
        self.assertEqual(dumped["company_requisites"], {"error": "PDF не читаем"})

    def test_build_order_response_empty_jsonb_returns_none(self) -> None:
        order = _mock_order(parsed_params=None, survey_data=None, company_requisites=None)
        resp = build_order_response(order)
        self.assertIsNone(resp.parsed_params)
        self.assertIsNone(resp.survey_data)
        self.assertIsNone(resp.company_requisites)

    def test_build_order_response_handles_invalid_parsed_params(self) -> None:
        """Грязные parsed_params → `None` + WARN (не падаем на model_validate)."""
        order = _mock_order(
            parsed_params={"heat_loads": {"heating_load": "not a number"}},
            order_type=OrderType.CUSTOM,
        )
        with self.assertLogs("app.repositories.order_jsonb", level="WARNING") as cm:
            resp = build_order_response(order)
        self.assertIsNone(resp.parsed_params)
        self.assertTrue(any("parsed_params невалидны" in m for m in cm.output))

    def test_build_order_response_handles_invalid_survey_data(self) -> None:
        # `floors` вне диапазона 0..200 → ValidationError в SurveyData
        order = _mock_order(
            survey_data={"floors": 9999},
            order_type=OrderType.CUSTOM,
        )
        with self.assertLogs("app.repositories.order_jsonb", level="WARNING"):
            resp = build_order_response(order)
        self.assertIsNone(resp.survey_data)

    def test_missing_params_preserves_legacy_codes(self) -> None:
        """В БД могут быть legacy-коды — отдаём как есть (не роняем ответ)."""
        order = _mock_order(
            missing_params=["floor_plan", "balance_act"],
            status=OrderStatus.WAITING_CLIENT_INFO,
        )
        resp = build_order_response(order)
        self.assertEqual(resp.missing_params, ["floor_plan", "balance_act"])

    def test_missing_params_empty_becomes_none(self) -> None:
        order = _mock_order(missing_params=[])
        resp = build_order_response(order)
        self.assertIsNone(resp.missing_params)

    def test_company_requisites_for_response_helper(self) -> None:
        # error-маркер
        order_err = _mock_order(company_requisites={"error": "oops"})
        got = company_requisites_for_response(order_err)
        self.assertIsInstance(got, CompanyRequisitesError)

        # нормальные реквизиты
        order_ok = _mock_order(
            company_requisites={
                "full_name": "ООО Теплосеть",
                "inn": "7712345678",
                "bik": "044525225",
                "settlement_account": "40702810900000000001",
            }
        )
        got_ok = company_requisites_for_response(order_ok)
        self.assertIsInstance(got_ok, CompanyRequisites)

        # пусто
        self.assertIsNone(company_requisites_for_response(_mock_order()))


class UploadPageInfoTypingTests(unittest.TestCase):
    def test_upload_page_info_typed_fields(self) -> None:
        ann = UploadPageInfo.__annotations__
        self.assertIn("TUParsedData", str(ann["parsed_params"]))
        self.assertIn("SurveyData", str(ann["survey_data"]))
        self.assertIn("CompanyRequisites", str(ann["company_requisites"]))


class CompanyRequisitesResponseAliasTests(unittest.TestCase):
    def test_alias_is_union(self) -> None:
        alias = str(CompanyRequisitesResponse)
        self.assertIn("CompanyRequisites", alias)
        self.assertIn("CompanyRequisitesError", alias)


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main()
