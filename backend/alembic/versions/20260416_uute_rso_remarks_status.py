"""add rso remarks received order status

Revision ID: 20260416_uute_rso_remarks_status
Revises: 20260416_uute_final_payment_rso_feedback
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "20260416_uute_rso_remarks_status"
down_revision: Union[str, None] = "20260416_uute_final_payment_rso_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(
                text(
                    "ALTER TYPE order_status ADD VALUE IF NOT EXISTS "
                    "'RSO_REMARKS_RECEIVED'"
                )
            )
        op.execute(
            text(
                """
                WITH latest_remarks AS (
                    SELECT order_id, MAX(created_at) AS latest_remarks_at
                    FROM order_files
                    WHERE category = 'RSO_REMARKS'
                    GROUP BY order_id
                ),
                latest_projects AS (
                    SELECT order_id, MAX(created_at) AS latest_project_at
                    FROM order_files
                    WHERE category = 'GENERATED_PROJECT'
                    GROUP BY order_id
                )
                UPDATE orders AS o
                SET status = 'RSO_REMARKS_RECEIVED'
                FROM latest_remarks AS lr
                LEFT JOIN latest_projects AS lp ON lp.order_id = lr.order_id
                WHERE o.id = lr.order_id
                  AND o.status = 'AWAITING_FINAL_PAYMENT'
                  AND o.final_paid_at IS NULL
                  AND (
                    lp.latest_project_at IS NULL
                    OR lr.latest_remarks_at >= lp.latest_project_at
                  );
                """
            )
        )


def downgrade() -> None:
    # PostgreSQL не поддерживает безопасное удаление enum labels в общем случае.
    pass
