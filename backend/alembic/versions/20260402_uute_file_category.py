"""Категории файлов УУТЭ: balance_act, connection_plan; перенос floor_plan.

Revision ID: 20260402_uute_fc
Revises:
Create Date: 2026-04-02

"""
from alembic import op
from sqlalchemy import text

revision = "20260402_uute_fc"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect != "postgresql":
        return

    op.execute(
        text("""
        DO $body$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'file_category') THEN
            IF NOT EXISTS (
              SELECT 1 FROM pg_enum e
              JOIN pg_type t ON e.enumtypid = t.oid
              WHERE t.typname = 'file_category' AND e.enumlabel = 'balance_act'
            ) THEN
              ALTER TYPE file_category ADD VALUE 'balance_act';
            END IF;
            IF NOT EXISTS (
              SELECT 1 FROM pg_enum e
              JOIN pg_type t ON e.enumtypid = t.oid
              WHERE t.typname = 'file_category' AND e.enumlabel = 'connection_plan'
            ) THEN
              ALTER TYPE file_category ADD VALUE 'connection_plan';
            END IF;
          END IF;
        END$body$;
        """)
    )

    op.execute(
        text("""
        UPDATE order_files
        SET category = 'other'
        WHERE category::text = 'floor_plan';
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
                  WHEN 'floor_plan' THEN 'balance_act'
                  WHEN 'connection_scheme' THEN NULL
                  WHEN 'system_type' THEN NULL
                  ELSE t.val
                END AS new_val
              FROM jsonb_array_elements_text(COALESCE(o.missing_params, '[]'::jsonb))
                WITH ORDINALITY AS t(val, ord)
            ) x
            WHERE x.new_val IS NOT NULL
          ),
          '[]'::jsonb
        )
        WHERE o.missing_params IS NOT NULL
          AND jsonb_array_length(COALESCE(o.missing_params, '[]'::jsonb)) > 0;
        """)
    )


def downgrade() -> None:
    pass
