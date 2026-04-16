import unittest
from pathlib import Path


ADMIN_HTML_PATH = Path(__file__).resolve().parents[1] / "static" / "admin.html"


class AdminPostProjectActionsTests(unittest.TestCase):
    def test_rso_remarks_actions_use_derived_flag_fallback(self) -> None:
        source = ADMIN_HTML_PATH.read_text(encoding="utf-8")

        self.assertIn("order.has_rso_remarks", source)
        self.assertIn(
            "status === 'rso_remarks_received' || order.has_rso_remarks",
            source,
        )
        self.assertIn("/resend-corrected-project", source)


if __name__ == "__main__":
    unittest.main()
