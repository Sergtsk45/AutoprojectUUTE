import unittest
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260416_uute_rso_remarks_status.py"
)


class RsoStatusMigrationTests(unittest.TestCase):
    def test_migration_uses_safe_rso_status_backfill(self) -> None:
        source = MIGRATION_PATH.read_text(encoding="utf-8")
        normalized = " ".join(source.replace('"', "'").split())

        self.assertIn("autocommit_block()", source)
        self.assertIn("ALTER TYPE order_status ADD VALUE IF NOT EXISTS", normalized)
        self.assertIn("RSO_REMARKS_RECEIVED", normalized)
        self.assertIn("o.final_paid_at IS NULL", normalized)
        self.assertIn("latest_project_at", source)
        self.assertIn("latest_remarks_at", source)
        self.assertIn("WHERE category = 'GENERATED_PROJECT'", normalized)
        self.assertIn("lr.latest_remarks_at >= lp.latest_project_at", normalized)
        self.assertNotIn("DO $body$", source)


if __name__ == "__main__":
    unittest.main()
