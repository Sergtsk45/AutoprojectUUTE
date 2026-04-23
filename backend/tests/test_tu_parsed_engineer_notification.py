"""Tests for engineer notification after TU parsing."""

import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.models.models import OrderStatus
from app.services import tasks


class _SessionStub:
    def commit(self) -> None:
        return None


class _SessionContextStub:
    def __init__(self, session: _SessionStub) -> None:
        self._session = session

    def __enter__(self) -> _SessionStub:
        return self._session

    def __exit__(self, *args) -> None:
        return None


class TuParsedEngineerNotificationTests(unittest.TestCase):
    def test_check_data_completeness_queues_engineer_notification(self) -> None:
        order_id = uuid.uuid4()
        order = SimpleNamespace(
            id=order_id,
            status=OrderStatus.TU_PARSED,
            files=[],
            missing_params=[],
            waiting_client_info_at=None,
            survey_data=None,
        )
        notify_task = Mock()

        with (
            patch.object(
                tasks,
                "SyncSession",
                return_value=_SessionContextStub(_SessionStub()),
            ),
            patch.object(tasks, "_get_order", return_value=order),
            patch.object(
                tasks,
                "compute_client_document_missing",
                return_value=["heat_scheme"],
            ),
            patch.object(
                tasks,
                "_transition",
                side_effect=lambda _session, current_order, new_status: setattr(
                    current_order, "status", new_status
                ),
            ),
            patch.object(tasks.send_info_request_email, "apply_async") as send_info_mock,
            patch.object(
                tasks,
                "notify_engineer_tu_parsed",
                new=notify_task,
                create=True,
            ),
        ):
            tasks.check_data_completeness.run(str(order_id))

        send_info_mock.assert_called_once()
        notify_task.delay.assert_called_once_with(str(order_id))
        self.assertEqual(order.status, OrderStatus.WAITING_CLIENT_INFO)
        self.assertIn("company_card", order.missing_params)


if __name__ == "__main__":
    unittest.main()
