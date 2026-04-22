import unittest
from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
ADMIN_HTML_PATH = STATIC_DIR / "admin.html"
ADMIN_JS_DIR = STATIC_DIR / "js" / "admin"


def _admin_sources() -> str:
    """Склеивает admin.html и все JS-модули в одну строку.

    После фазы E3 (2026-04-22) inline-скрипт разнесён по модулям
    backend/static/js/admin/*.js, поэтому здесь склеиваем все
    файлы, чтобы проверки contract-типа assertIn оставались
    устойчивыми к внутренней реорганизации модулей.
    """
    parts = [ADMIN_HTML_PATH.read_text(encoding="utf-8")]
    for js_file in sorted(ADMIN_JS_DIR.glob("*.js")):
        parts.append(js_file.read_text(encoding="utf-8"))
    return "\n".join(parts)


class AdminPostProjectActionsTests(unittest.TestCase):
    def test_rso_remarks_actions_use_derived_flag_fallback(self) -> None:
        source = _admin_sources()

        self.assertIn("order.has_rso_remarks", source)
        self.assertIn(
            "status === 'rso_remarks_received' || order.has_rso_remarks",
            source,
        )
        self.assertIn("/resend-corrected-project", source)

    def test_load_calc_config_restores_panel_state_only_on_order_change(self) -> None:
        source = _admin_sources()

        self.assertIn(
            "const _det = document.getElementById('calcConfigDetails');",
            source,
        )
        self.assertIn(
            "const isOrderChange = !_det || _det.dataset.orderId !== String(orderId);",
            source,
        )
        self.assertIn("if (isOrderChange) {", source)
        self.assertIn("applyCalcConfigDetailsState(orderId);", source)


if __name__ == "__main__":
    unittest.main()
