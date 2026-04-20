"""add signed contract enum labels

Revision ID: 20260416_uute_signed_contract_enums
Revises: 87fcef6f52ff
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "20260416_uute_signed_contract_enums"
down_revision: Union[str, None] = "87fcef6f52ff"
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
                    WHERE t.typname = 'file_category' AND e.enumlabel = 'SIGNED_CONTRACT'
                  ) THEN
                    ALTER TYPE file_category ADD VALUE 'SIGNED_CONTRACT';
                  END IF;
                END$body$;
                """
            )
        )
        op.execute(
            text(
                """
                DO $body$
                BEGIN
                  IF NOT EXISTS (
                    SELECT 1 FROM pg_enum e
                    JOIN pg_type t ON e.enumtypid = t.oid
                    WHERE t.typname = 'email_type' AND e.enumlabel = 'SIGNED_CONTRACT_NOTIFICATION'
                  ) THEN
                    ALTER TYPE email_type ADD VALUE 'SIGNED_CONTRACT_NOTIFICATION';
                  END IF;
                END$body$;
                """
            )
        )


def downgrade() -> None:
    # PostgreSQL не поддерживает безопасное удаление enum labels в общем случае.
    pass
