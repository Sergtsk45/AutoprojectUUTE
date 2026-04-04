"""Переименование значений file_category: balance_act/connection_plan → UPPER_CASE.

Revision ID: 20260403_fc_upper
Revises: 20260402_uute_fc
Create Date: 2026-04-03

"""
from alembic import op
from sqlalchemy import text

revision = "20260403_fc_upper"
down_revision = "20260402_uute_fc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        text("""
        DO $body$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'file_category' AND e.enumlabel = 'balance_act'
          ) THEN
            ALTER TYPE file_category RENAME VALUE 'balance_act' TO 'BALANCE_ACT';
          END IF;
          IF EXISTS (
            SELECT 1 FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'file_category' AND e.enumlabel = 'connection_plan'
          ) THEN
            ALTER TYPE file_category RENAME VALUE 'connection_plan' TO 'CONNECTION_PLAN';
          END IF;
        END$body$;
        """)
    )

    op.execute(
        text("""
        UPDATE orders o
        SET missing_params = COALESCE(
          (
            SELECT jsonb_agg(to_jsonb(x.new_val) ORDER BY x.ord)
            FROM (
              SELECT
                t.ord,
                CASE t.val
                  WHEN 'balance_act' THEN 'BALANCE_ACT'
                  WHEN 'connection_plan' THEN 'CONNECTION_PLAN'
                  ELSE t.val
                END AS new_val
              FROM jsonb_array_elements_text(COALESCE(o.missing_params, '[]'::jsonb))
                WITH ORDINALITY AS t(val, ord)
            ) x
          ),
          '[]'::jsonb
        )
        WHERE o.missing_params IS NOT NULL
          AND jsonb_array_length(COALESCE(o.missing_params, '[]'::jsonb)) > 0;
        """)
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        text("""
        UPDATE orders o
        SET missing_params = COALESCE(
          (
            SELECT jsonb_agg(to_jsonb(x.new_val) ORDER BY x.ord)
            FROM (
              SELECT
                t.ord,
                CASE t.val
                  WHEN 'BALANCE_ACT' THEN 'balance_act'
                  WHEN 'CONNECTION_PLAN' THEN 'connection_plan'
                  ELSE t.val
                END AS new_val
              FROM jsonb_array_elements_text(COALESCE(o.missing_params, '[]'::jsonb))
                WITH ORDINALITY AS t(val, ord)
            ) x
          ),
          '[]'::jsonb
        )
        WHERE o.missing_params IS NOT NULL
          AND jsonb_array_length(COALESCE(o.missing_params, '[]'::jsonb)) > 0;
        """)
    )

    op.execute(
        text("""
        DO $body$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'file_category' AND e.enumlabel = 'BALANCE_ACT'
          ) THEN
            ALTER TYPE file_category RENAME VALUE 'BALANCE_ACT' TO 'balance_act';
          END IF;
          IF EXISTS (
            SELECT 1 FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'file_category' AND e.enumlabel = 'CONNECTION_PLAN'
          ) THEN
            ALTER TYPE file_category RENAME VALUE 'CONNECTION_PLAN' TO 'connection_plan';
          END IF;
        END$body$;
        """)
    )
