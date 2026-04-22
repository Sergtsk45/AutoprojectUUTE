"""Тесты нормализации FileCategory (фазы B2.a → B2.b аудита).

После B2.b (2026-04-22):
- `.value` всех членов — snake_case lowercase;
- `FileCategory("BALANCE_ACT")` бросает `ValueError` (compat-shim удалён);
- `param_labels` больше не канонизирует legacy UPPER_CASE-коды;
- `SAMPLE_DOCUMENTS` содержит образцы под каждый lowercase-код.
"""

from __future__ import annotations

import logging
import re
import unittest

from app.models.models import FileCategory
from app.services.param_labels import (
    CLIENT_DOCUMENT_PARAM_CODES,
    MISSING_PARAM_LABELS,
    SAMPLE_DOCUMENTS,
    client_document_list_needs_migration,
    get_missing_items,
    get_sample_paths,
)


class FileCategoryValuesTests(unittest.TestCase):
    def test_all_values_are_snake_case_lowercase(self) -> None:
        pattern = re.compile(r"^[a-z][a-z0-9_]*$")
        for member in FileCategory:
            self.assertRegex(
                member.value,
                pattern,
                f"{member.name} имеет non-snake_case .value={member.value!r}",
            )

    def test_specific_values_after_b2(self) -> None:
        self.assertEqual(FileCategory.BALANCE_ACT.value, "balance_act")
        self.assertEqual(FileCategory.CONNECTION_PLAN.value, "connection_plan")

    def test_missing_rejects_legacy_uppercase(self) -> None:
        """B2.b: API больше не принимает UPPER_CASE коды."""
        with self.assertRaises(ValueError):
            FileCategory("BALANCE_ACT")
        with self.assertRaises(ValueError):
            FileCategory("CONNECTION_PLAN")

    def test_missing_rejects_mixed_case(self) -> None:
        with self.assertRaises(ValueError):
            FileCategory("Connection_Plan")

    def test_missing_rejects_garbage(self) -> None:
        with self.assertRaises(ValueError):
            FileCategory("not_a_category")

    def test_canonical_lowercase_lookup_still_works(self) -> None:
        self.assertIs(FileCategory("balance_act"), FileCategory.BALANCE_ACT)
        self.assertIs(FileCategory("connection_plan"), FileCategory.CONNECTION_PLAN)
        self.assertIs(FileCategory("tu"), FileCategory.TU)


class ParamLabelsTests(unittest.TestCase):
    def test_client_document_codes_are_lowercase(self) -> None:
        for code in CLIENT_DOCUMENT_PARAM_CODES:
            self.assertEqual(code, code.lower())

    def test_labels_cover_all_client_document_codes(self) -> None:
        for code in CLIENT_DOCUMENT_PARAM_CODES:
            self.assertIn(code, MISSING_PARAM_LABELS, f"нет подписи для {code!r}")

    def test_samples_cover_document_codes_except_company_card(self) -> None:
        # `company_card` — без образца (специфично для каждой организации)
        expected = set(CLIENT_DOCUMENT_PARAM_CODES) - {"company_card"}
        self.assertEqual(set(SAMPLE_DOCUMENTS.keys()), expected)

    def test_get_missing_items_returns_canonical_labels(self) -> None:
        items = get_missing_items(["balance_act", "heat_point_plan"])
        self.assertEqual(len(items), 2)
        self.assertIn("Акт разграничения", items[0]["label"])
        self.assertIn("теплового пункта", items[1]["label"])

    def test_get_missing_items_no_longer_canonicalizes_uppercase(self) -> None:
        """B2.b: legacy UPPER_CASE отображается как plain text без подписи."""
        items = get_missing_items(["BALANCE_ACT"])
        self.assertEqual(items, [{"label": "BALANCE_ACT", "hint": ""}])

    def test_get_sample_paths_only_for_canonical_codes(self) -> None:
        self.assertEqual(
            get_sample_paths(["balance_act", "connection_plan"]),
            [
                "samples/sample_balance_act.pdf",
                "samples/sample_connection_plan.pdf",
            ],
        )

    def test_get_sample_paths_ignores_legacy_uppercase(self) -> None:
        """B2.b: UPPER_CASE-коды больше не находят образцы."""
        self.assertEqual(get_sample_paths(["BALANCE_ACT", "CONNECTION_PLAN"]), [])

    def test_legacy_data_still_triggers_migration_flag(self) -> None:
        """`client_document_list_needs_migration` реагирует на чужие коды.

        После B2.b UPPER_CASE-кодов в `_LEGACY_DOCUMENT_PARAM_CODES` нет, но
        они всё равно ловятся правилом «любой код вне канонических четырёх».
        """
        self.assertTrue(client_document_list_needs_migration(["floor_plan"]))
        self.assertTrue(client_document_list_needs_migration(["BALANCE_ACT", "heat_scheme"]))
        self.assertFalse(client_document_list_needs_migration(list(CLIENT_DOCUMENT_PARAM_CODES)))


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main()
