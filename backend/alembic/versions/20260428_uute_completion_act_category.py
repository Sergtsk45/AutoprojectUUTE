"""add completion_act file category

Revision ID: 20260428_uute_completion_act
Revises: 20260422_uute_drop_legacy_statuses
Create Date: 2026-04-28

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "20260428_uute_completion_act"
down_revision: Union[str, None] = "20260422_uute_drop_legacy_statuses"
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
                    WHERE t.typname = 'file_category' AND e.enumlabel = 'COMPLETION_ACT'
                  ) THEN
                    ALTER TYPE file_category ADD VALUE 'COMPLETION_ACT';
                  END IF;
                END$body$;
                """
            )
        )


def downgrade() -> None:
    # PostgreSQL не поддерживает безопасное удаление enum labels в общем случае.
    pass
