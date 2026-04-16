"""add tu parsed notification email enum

Revision ID: 20260416_uute_tu_parsed_notification
Revises: 20260416_uute_rso_remarks_status
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "20260416_uute_tu_parsed_notification"
down_revision: Union[str, None] = "20260416_uute_rso_remarks_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            text(
                """
                DO $body$
                BEGIN
                  IF NOT EXISTS (
                    SELECT 1 FROM pg_enum e
                    JOIN pg_type t ON e.enumtypid = t.oid
                    WHERE t.typname = 'email_type' AND e.enumlabel = 'TU_PARSED_NOTIFICATION'
                  ) THEN
                    ALTER TYPE email_type ADD VALUE 'TU_PARSED_NOTIFICATION';
                  END IF;
                END$body$;
                """
            )
        )


def downgrade() -> None:
    # PostgreSQL не поддерживает безопасное удаление enum labels в общем случае.
    pass
