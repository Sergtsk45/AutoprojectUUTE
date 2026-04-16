"""add final payment rso feedback artifacts

Revision ID: 20260416_uute_final_payment_rso_feedback
Revises: 20260416_uute_signed_contract_enums
Create Date: 2026-04-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


revision: str = "20260416_uute_final_payment_rso_feedback"
down_revision: Union[str, None] = "20260416_uute_signed_contract_enums"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for enum_label in ("FINAL_INVOICE", "RSO_REMARKS"):
            op.execute(
                text(
                    f"""
                    DO $body$
                    BEGIN
                      IF NOT EXISTS (
                        SELECT 1 FROM pg_enum e
                        JOIN pg_type t ON e.enumtypid = t.oid
                        WHERE t.typname = 'file_category' AND e.enumlabel = '{enum_label}'
                      ) THEN
                        ALTER TYPE file_category ADD VALUE '{enum_label}';
                      END IF;
                    END$body$;
                    """
                )
            )

    op.add_column(
        "orders",
        sa.Column("rso_scan_received_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        text(
            """
            UPDATE orders AS o
            SET rso_scan_received_at = src.first_rso_scan_at
            FROM (
                SELECT order_id, MIN(created_at) AS first_rso_scan_at
                FROM order_files
                WHERE category = 'RSO_SCAN'
                GROUP BY order_id
            ) AS src
            WHERE o.id = src.order_id
              AND o.rso_scan_received_at IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("orders", "rso_scan_received_at")
    # PostgreSQL не поддерживает безопасное удаление enum labels в общем случае.
