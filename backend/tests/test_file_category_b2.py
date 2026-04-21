"""Тесты нормализации FileCategory (фаза B2.a аудита).

Проверяем:
- каноническое `.value` всех членов — snake_case lowercase;
- `_missing_` принимает устаревшие UPPER_CASE значения как алиас;
- `param_labels` возвращает корректные лейблы и для lowercase, и для legacy
  UPPER_CASE кодов (B2 compat-shim);
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
    _canonicalize,
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

    def test_missing_accepts_legacy_uppercase(self) -> None:
        with self.assertLogs("app.models.models", level="WARNING") as cm:
            cat = FileCategory("BALANCE_ACT")
        self.assertIs(cat, FileCategory.BALANCE_ACT)
        self.assertTrue(any("устаревший uppercase-алиас" in m for m in cm.output))

    def test_missing_accepts_mixed_case(self) -> None:
        with self.assertLogs("app.models.models", level="WARNING"):
            cat = FileCategory("Connection_Plan")
        self.assertIs(cat, FileCategory.CONNECTION_PLAN)

    def test_missing_rejects_garbage(self) -> None:
        with self.assertRaises(ValueError):
            FileCategory("not_a_category")


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

    def test_canonicalize_legacy_uppercase(self) -> None:
        self.assertEqual(_canonicalize("BALANCE_ACT"), "balance_act")
        self.assertEqual(_canonicalize("CONNECTION_PLAN"), "connection_plan")
        self.assertEqual(_canonicalize("heat_scheme"), "heat_scheme")

    def test_get_missing_items_works_on_legacy_codes(self) -> None:
        """Письмо клиенту не сломается, если в missing_params остался UPPER_CASE."""
        items = get_missing_items(["BALANCE_ACT", "heat_point_plan"])
        self.assertEqual(len(items), 2)
        self.assertIn("Акт разграничения", items[0]["label"])

    def test_get_sample_paths_works_on_legacy_codes(self) -> None:
        paths = get_sample_paths(["BALANCE_ACT", "CONNECTION_PLAN"])
        self.assertEqual(
            paths,
            [
                "samples/sample_balance_act.pdf",
                "samples/sample_connection_plan.pdf",
            ],
        )

    def test_legacy_uppercase_triggers_migration_flag(self) -> None:
        """`client_document_list_needs_migration` должен ловить UPPER_CASE коды."""
        self.assertTrue(client_document_list_needs_migration(["BALANCE_ACT", "heat_scheme"]))
        self.assertFalse(client_document_list_needs_migration(list(CLIENT_DOCUMENT_PARAM_CODES)))


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main()
