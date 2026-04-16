import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.models.models import ALLOWED_TRANSITIONS, FileCategory, OrderStatus
from app.post_project_state import derive_post_project_flags


def _file(category: FileCategory, created_at: datetime) -> SimpleNamespace:
    return SimpleNamespace(category=category, created_at=created_at)


class PostProjectStatusTests(unittest.TestCase):
    def test_status_loop_allows_return_from_rso_remarks(self) -> None:
        self.assertIn(
            OrderStatus.RSO_REMARKS_RECEIVED,
            ALLOWED_TRANSITIONS[OrderStatus.AWAITING_FINAL_PAYMENT],
        )
        self.assertIn(
            OrderStatus.AWAITING_FINAL_PAYMENT,
            ALLOWED_TRANSITIONS[OrderStatus.RSO_REMARKS_RECEIVED],
        )

    def test_pending_rso_remarks_follow_open_status(self) -> None:
        now = datetime.now(timezone.utc)
        flags = derive_post_project_flags(
            files=[
                _file(FileCategory.RSO_SCAN, now - timedelta(days=2)),
                _file(FileCategory.RSO_REMARKS, now - timedelta(days=1)),
            ],
            final_paid_at=None,
            order_status=OrderStatus.RSO_REMARKS_RECEIVED,
        )

        self.assertTrue(flags["has_rso_scan"])
        self.assertTrue(flags["has_rso_remarks"])
        self.assertFalse(flags["awaiting_rso_feedback"])

    def test_old_remarks_do_not_block_after_new_project_resend(self) -> None:
        now = datetime.now(timezone.utc)
        flags = derive_post_project_flags(
            files=[
                _file(FileCategory.RSO_SCAN, now - timedelta(days=4)),
                _file(FileCategory.RSO_REMARKS, now - timedelta(days=3)),
                _file(FileCategory.GENERATED_PROJECT, now - timedelta(days=1)),
            ],
            final_paid_at=None,
            order_status=OrderStatus.AWAITING_FINAL_PAYMENT,
        )

        self.assertTrue(flags["has_rso_scan"])
        self.assertFalse(flags["has_rso_remarks"])
        self.assertTrue(flags["awaiting_rso_feedback"])


if __name__ == "__main__":
    unittest.main()
