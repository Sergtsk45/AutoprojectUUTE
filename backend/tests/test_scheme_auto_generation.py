"""
@file: test_scheme_auto_generation.py
@description: Тесты автогенерации PDF схемы и обновлённой логики missing_params.
@dependencies: pytest, app.services.param_labels, app.services.tasks
@created: 2026-04-23
"""

import pytest

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
