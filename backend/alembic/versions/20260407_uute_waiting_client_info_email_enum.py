"""waiting_client_info_at + email_type client_documents_received

Revision ID: 20260407_uute_wci
Revises: rename_standard_to_custom
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "20260407_uute_wci"
down_revision: Union[str, None] = "rename_standard_to_custom"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("waiting_client_info_at", sa.DateTime(timezone=True), nullable=True),
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            text("""
            DO $body$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'email_type' AND e.enumlabel = 'CLIENT_DOCUMENTS_RECEIVED'
              ) THEN
                ALTER TYPE email_type ADD VALUE 'CLIENT_DOCUMENTS_RECEIVED';
              END IF;
            END$body$;
            """)
        )

        op.execute(
            text("""
            UPDATE orders
            SET waiting_client_info_at = (NOW() AT TIME ZONE 'utc') - interval '25 hours'
            WHERE status = 'WAITING_CLIENT_INFO'::order_status
              AND waiting_client_info_at IS NULL;
            """)
        )


def downgrade() -> None:
    op.drop_column("orders", "waiting_client_info_at")
