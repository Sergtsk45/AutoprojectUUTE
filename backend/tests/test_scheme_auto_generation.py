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


class TestComputeClientDocumentMissing:
    """Тесты функции compute_client_document_missing с учётом scheme_config."""

    def test_all_documents_uploaded_returns_empty(self):
        uploaded = set(CLIENT_DOCUMENT_PARAM_CODES)
        result = compute_client_document_missing(uploaded)
        assert result == []

    def test_no_documents_uploaded_returns_all(self):
        result = compute_client_document_missing(set())
        assert set(result) == set(CLIENT_DOCUMENT_PARAM_CODES)

    def test_heat_scheme_excluded_when_scheme_config_present(self):
        """Если в survey_data есть scheme_config, heat_scheme не должен быть в missing."""
        uploaded = {"BALANCE_ACT", "CONNECTION_PLAN", "heat_point_plan", "company_card"}
        survey_data = {"scheme_config": {"connection_type": "dependent"}}
        result = compute_client_document_missing(uploaded, survey_data)
        assert "heat_scheme" not in result

    def test_heat_scheme_required_when_no_scheme_config(self):
        """Если scheme_config отсутствует, heat_scheme должен быть в missing."""
        uploaded = {"BALANCE_ACT", "CONNECTION_PLAN", "heat_point_plan", "company_card"}
        result = compute_client_document_missing(uploaded, survey_data=None)
        assert "heat_scheme" in result

    def test_heat_scheme_required_when_empty_survey_data(self):
        uploaded = {"BALANCE_ACT", "CONNECTION_PLAN", "heat_point_plan", "company_card"}
        result = compute_client_document_missing(uploaded, survey_data={})
        assert "heat_scheme" in result

    def test_other_missing_documents_still_reported(self):
        """heat_scheme исключается, но остальные отсутствующие документы возвращаются."""
        uploaded = {"heat_scheme"}
        survey_data = {"scheme_config": {"connection_type": "dependent"}}
        result = compute_client_document_missing(uploaded, survey_data)
        expected = {c for c in CLIENT_DOCUMENT_PARAM_CODES if c != "heat_scheme"}
        assert set(result) == expected

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

    def test_success_with_valid_config(self, tmp_path, monkeypatch):
        """Успешная генерация создаёт файл и OrderFile."""
        from app.services.tasks import client_response as cr

        monkeypatch.setattr(cr.settings, "upload_dir", tmp_path)

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

        with patch(
            "app.services.scheme_pdf_renderer.render_scheme_pdf", return_value=b"%PDF-fake-bytes"
        ):
            result = cr._auto_generate_scheme_if_configured(session, order)

        assert result is True
        session.add.assert_called_once()
        added_file = session.add.call_args[0][0]
        assert added_file.category == FileCategory.HEAT_SCHEME
        assert added_file.order_id == order.id
        assert added_file.file_size == len(b"%PDF-fake-bytes")
        session.commit.assert_called()

        scheme_dir = tmp_path / str(order.id) / "heat_scheme"
        assert scheme_dir.exists()
        assert any(scheme_dir.iterdir()), "PDF file must be written"

    def test_invalid_config_returns_false(self, tmp_path, monkeypatch):
        """Недопустимая комбинация параметров → False, файл не создаётся."""
        from app.services.tasks import client_response as cr

        monkeypatch.setattr(cr.settings, "upload_dir", tmp_path)

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

        monkeypatch.setattr(cr.settings, "upload_dir", tmp_path)

        session = MagicMock()
        order = self._make_order_mock(survey_data={})

        result = cr._auto_generate_scheme_if_configured(session, order)
        assert result is False
        session.add.assert_not_called()

    def test_pdf_render_exception_returns_false(self, tmp_path, monkeypatch):
        """Если WeasyPrint падает, функция возвращает False без пробрасывания."""
        from app.services.tasks import client_response as cr

        monkeypatch.setattr(cr.settings, "upload_dir", tmp_path)

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

        with patch(
            "app.services.scheme_pdf_renderer.render_scheme_pdf",
            side_effect=RuntimeError("WeasyPrint error"),
        ):
            result = cr._auto_generate_scheme_if_configured(session, order)

        assert result is False
        session.add.assert_not_called()


class TestProcessClientResponseIntegration:
    """Интеграционные тесты: process_client_response + автогенерация."""

    def test_heat_scheme_not_in_missing_when_auto_generated(self, tmp_path, monkeypatch):
        """После успешной автогенерации heat_scheme отсутствует в missing_params."""
        from app.services.tasks import client_response as cr

        monkeypatch.setattr(cr.settings, "upload_dir", tmp_path)

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

        def fake_add(obj):
            order.files.append(MagicMock(category=MagicMock(value="heat_scheme")))

        session.add.side_effect = fake_add

        with patch("app.services.scheme_pdf_renderer.render_scheme_pdf", return_value=b"%PDF"):
            success = cr._auto_generate_scheme_if_configured(session, order)

        assert success is True
        uploaded = {f.category.value for f in order.files}
        assert "heat_scheme" in uploaded

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
