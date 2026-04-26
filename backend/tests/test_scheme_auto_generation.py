"""
@file: test_scheme_auto_generation.py
@description: Тесты автогенерации PDF схемы и обновлённой логики missing_params.
@dependencies: app.services.param_labels, app.services.tasks
@created: 2026-04-23
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.models import FileCategory
from app.services.param_labels import (
    CLIENT_DOCUMENT_PARAM_CODES,
    compute_client_document_missing,
)
from app.schemas.scheme import SchemeParams, SchemeType


class TestSchemePreviewApi:
    """Тесты клиентского preview-only конфигуратора схем."""

    @pytest.mark.asyncio
    async def test_preview_returns_standalone_svg_without_gost_frame(self, monkeypatch):
        from app.api import scheme_generator as api
        from app.schemas.scheme import SchemeConfig, SchemeGenerateRequest

        monkeypatch.setattr(api, "render_scheme", lambda scheme_type, params: '<g id="demo"></g>')

        response = await api.preview_scheme(
            SchemeGenerateRequest(
                config=SchemeConfig(
                    connection_type="dependent",
                    has_valve=False,
                    has_gwp=False,
                    has_ventilation=False,
                )
            )
        )

        assert response.svg_content.startswith("<svg")
        assert 'id="demo"' in response.svg_content
        assert "gost-stamp" not in response.svg_content
        assert "gost-working-area" not in response.svg_content

    @pytest.mark.asyncio
    async def test_public_pdf_generation_is_disabled(self):
        from fastapi import HTTPException

        from app.api.scheme_generator import generate_scheme_pdf
        from app.schemas.scheme import SchemeConfig, SchemeGenerateRequest

        with pytest.raises(HTTPException) as exc_info:
            await generate_scheme_pdf(
                uuid.uuid4(),
                SchemeGenerateRequest(
                    config=SchemeConfig(
                        connection_type="dependent",
                        has_valve=False,
                        has_gwp=False,
                        has_ventilation=False,
                    )
                ),
            )

        assert exc_info.value.status_code == 410


class TestRenderSchemeTemplateIntegration:
    """Тесты подключения DXF-шаблонов к общему SVG-диспетчеру."""

    def test_dep_simple_returns_template_content_when_available(self, monkeypatch):
        from app.services import scheme_svg_renderer as renderer

        template_marker = '<g id="template-marker">template content</g>'
        monkeypatch.setattr(
            renderer,
            "render_template_scheme",
            lambda scheme_type, params: template_marker,
            raising=False,
        )

        result = renderer.render_scheme(SchemeType.DEP_SIMPLE, SchemeParams())

        assert result == template_marker

    def test_dep_simple_returns_empty_template_content_without_fallback(self, monkeypatch):
        from app.services import scheme_svg_renderer as renderer

        monkeypatch.setattr(
            renderer,
            "render_template_scheme",
            lambda scheme_type, params: "",
            raising=False,
        )

        result = renderer.render_scheme(SchemeType.DEP_SIMPLE, SchemeParams())

        assert result == ""

    def test_dep_simple_falls_back_to_programmatic_svg_when_template_missing(self, monkeypatch):
        from app.services import scheme_svg_renderer as renderer

        template_marker = '<g id="template-marker">template content</g>'
        monkeypatch.setattr(
            renderer,
            "render_template_scheme",
            lambda scheme_type, params: None,
            raising=False,
        )

        result = renderer.render_scheme(SchemeType.DEP_SIMPLE, SchemeParams())

        assert result != template_marker
        assert "Т1 (подача)" in result

    def test_other_scheme_type_falls_back_when_template_missing(self, monkeypatch):
        from app.services import scheme_svg_renderer as renderer

        monkeypatch.setattr(
            renderer,
            "render_template_scheme",
            lambda scheme_type, params: None,
            raising=False,
        )

        result = renderer.render_scheme(SchemeType.DEP_SIMPLE_GWP, SchemeParams())

        assert "Зона ГВС" in result


class TestComputeClientDocumentMissing:
    """Тесты функции compute_client_document_missing с учётом scheme_config."""

    def test_all_documents_uploaded_returns_empty(self):
        uploaded = set(CLIENT_DOCUMENT_PARAM_CODES)
        result = compute_client_document_missing(uploaded)
        assert result == []

    def test_no_documents_uploaded_returns_all(self):
        result = compute_client_document_missing(set())
        assert set(result) == set(CLIENT_DOCUMENT_PARAM_CODES)

    def test_heat_scheme_not_required_when_scheme_config_present(self):
        """Принципиальная схема больше не запрашивается у клиента как документ."""
        uploaded = {"BALANCE_ACT", "CONNECTION_PLAN", "heat_point_plan", "company_card"}
        survey_data = {"scheme_config": {"connection_type": "dependent"}}
        result = compute_client_document_missing(uploaded, survey_data)
        assert "heat_scheme" not in result

    def test_heat_scheme_not_required_without_scheme_config(self):
        uploaded = {"BALANCE_ACT", "CONNECTION_PLAN", "heat_point_plan", "company_card"}
        result = compute_client_document_missing(uploaded, survey_data=None)
        assert "heat_scheme" not in result

    def test_heat_scheme_not_required_when_empty_survey_data(self):
        uploaded = {"BALANCE_ACT", "CONNECTION_PLAN", "heat_point_plan", "company_card"}
        result = compute_client_document_missing(uploaded, survey_data={})
        assert "heat_scheme" not in result

    def test_other_missing_documents_still_reported(self):
        """Остальные отсутствующие документы возвращаются."""
        uploaded = set()
        survey_data = {"scheme_config": {"connection_type": "dependent"}}
        result = compute_client_document_missing(uploaded, survey_data)
        assert set(result) == set(CLIENT_DOCUMENT_PARAM_CODES)

    def test_backward_compatible_without_survey_data(self):
        """Вызов без survey_data работает как раньше."""
        uploaded = set()
        result = compute_client_document_missing(uploaded)
        assert set(result) == set(CLIENT_DOCUMENT_PARAM_CODES)


class TestAutoGenerateScheme:
    """Тесты функции _auto_generate_scheme_if_configured."""

    def _make_order_mock(self, survey_data=None, parsed_params=None):
        order = MagicMock()
        order.id = uuid.uuid4()
        order.survey_data = survey_data or {}
        order.parsed_params = parsed_params or {}
        order.object_address = "г. Москва, ул. Ленина, д. 1"
        order.client_organization = "ООО «Ромашка»"
        return order

    def test_client_pdf_generation_is_disabled(self, tmp_path):
        """Клиентский выбор схемы больше не создаёт PDF/OrderFile."""
        from app.services.tasks import client_response as cr

        session = MagicMock()
        order = self._make_order_mock(
            survey_data={
                "scheme_config": {
                    "connection_type": "dependent",
                    "has_valve": False,
                    "has_gwp": False,
                    "has_ventilation": False,
                }
            }
        )

        result = cr._auto_generate_scheme_if_configured(session, order)

        assert result is False
        session.add.assert_not_called()
        session.commit.assert_not_called()
        assert not (tmp_path / str(order.id) / "heat_scheme").exists()

    def test_invalid_config_returns_false(self, tmp_path, monkeypatch):
        """Недопустимая комбинация параметров → False, файл не создаётся."""
        from app.services.tasks import client_response as cr

        session = MagicMock()
        order = self._make_order_mock(
            survey_data={
                "scheme_config": {
                    "connection_type": "independent",
                    "has_valve": False,
                    "has_gwp": False,
                    "has_ventilation": False,
                }
            }
        )

        result = cr._auto_generate_scheme_if_configured(session, order)
        assert result is False
        session.add.assert_not_called()

    def test_missing_scheme_config_returns_false(self, tmp_path, monkeypatch):
        from app.services.tasks import client_response as cr

        session = MagicMock()
        order = self._make_order_mock(survey_data={})

        result = cr._auto_generate_scheme_if_configured(session, order)
        assert result is False
        session.add.assert_not_called()

    def test_pdf_render_is_not_called(self, tmp_path):
        from app.services.tasks import client_response as cr

        session = MagicMock()
        order = self._make_order_mock(
            survey_data={
                "scheme_config": {
                    "connection_type": "dependent",
                    "has_valve": False,
                    "has_gwp": False,
                    "has_ventilation": False,
                }
            }
        )

        with patch("app.services.scheme_pdf_renderer.render_scheme_pdf") as render_pdf:
            result = cr._auto_generate_scheme_if_configured(session, order)

        assert result is False
        render_pdf.assert_not_called()
        session.add.assert_not_called()


class TestProcessClientResponseIntegration:
    """Интеграционные тесты: process_client_response без клиентской PDF-генерации."""

    def test_heat_scheme_not_in_missing_without_auto_generation(self):
        """heat_scheme отсутствует в missing_params без создания PDF."""
        from app.services.tasks import client_response as cr

        session = MagicMock()
        order = MagicMock()
        order.id = uuid.uuid4()
        order.survey_data = {
            "scheme_config": {
                "connection_type": "dependent",
                "has_valve": False,
                "has_gwp": False,
                "has_ventilation": False,
            }
        }
        order.parsed_params = {}
        order.object_address = "ул. Ленина"
        order.client_organization = "ООО"

        existing_files = [
            MagicMock(category=MagicMock(value="BALANCE_ACT")),
            MagicMock(category=MagicMock(value="CONNECTION_PLAN")),
            MagicMock(category=MagicMock(value="heat_point_plan")),
            MagicMock(category=MagicMock(value="company_card")),
        ]
        order.files = list(existing_files)

        success = cr._auto_generate_scheme_if_configured(session, order)

        assert success is False
        session.add.assert_not_called()
        uploaded = {f.category.value for f in order.files}
        assert "heat_scheme" not in uploaded

        from app.services.param_labels import compute_client_document_missing

        missing = compute_client_document_missing(uploaded, order.survey_data)
        assert "heat_scheme" not in missing


class TestPublicSchemeDownload:
    """Тесты публичного скачивания PDF схемы клиентом."""

    @pytest.mark.asyncio
    async def test_download_returns_pdf_for_matching_heat_scheme_file(self, tmp_path, monkeypatch):
        from app.api.scheme_generator import download_generated_scheme_file
        from app.core.config import settings
        from app.models.models import OrderFile

        order_id = uuid.uuid4()
        file_id = uuid.uuid4()
        relative_path = f"{order_id}/heat_scheme/heat_scheme_test.pdf"
        pdf_path = tmp_path / relative_path
        pdf_path.parent.mkdir(parents=True)
        pdf_path.write_bytes(b"%PDF-1.4 test")

        monkeypatch.setattr(settings, "upload_dir", tmp_path)

        order_file = OrderFile(
            id=file_id,
            order_id=order_id,
            category=FileCategory.HEAT_SCHEME,
            original_filename="heat_scheme_test.pdf",
            storage_path=relative_path,
            content_type="application/pdf",
            file_size=pdf_path.stat().st_size,
        )

        result_proxy = MagicMock()
        result_proxy.scalar_one_or_none.return_value = order_file
        db = MagicMock()
        db.execute = AsyncMock(return_value=result_proxy)

        response = await download_generated_scheme_file(order_id, file_id, db)

        assert response.path == str(pdf_path)
        assert response.filename == "heat_scheme_test.pdf"
        assert response.media_type == "application/pdf"
