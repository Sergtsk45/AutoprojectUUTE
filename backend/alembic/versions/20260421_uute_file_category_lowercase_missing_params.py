"""Нормализация missing_params: BALANCE_ACT/CONNECTION_PLAN → snake_case lowercase.

Фаза B2.a аудита (non-breaking). Python-код переведён на lowercase `.value`,
а исторические значения в `orders.missing_params` (JSONB-массив строк)
нужно единоразово мигрировать, иначе письма «запрос документов» будут
использовать legacy-коды и `MISSING_PARAM_LABELS.get(code)` вернёт None.

ВАЖНО: PG-enum `file_category` (labels на `order_files.category`) **не
затрагивается** — там хранятся имена членов Python (`BALANCE_ACT`,
`CONNECTION_PLAN`), а не `.value`. Смена `.value` не требует RENAME VALUE.

Revision ID: 20260421_uute_fc_lower_missing
Revises: 20260416_uute_tu_parsed_notification
Create Date: 2026-04-21
"""

from alembic import op
from sqlalchemy import text

revision = "20260421_uute_fc_lower_missing"
down_revision = "20260416_uute_tu_parsed_notification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        text(
            """
            UPDATE orders o
            SET missing_params = COALESCE(
              (
                SELECT jsonb_agg(
                  to_jsonb(
                    CASE t.val
                      WHEN 'BALANCE_ACT' THEN 'balance_act'
                      WHEN 'CONNECTION_PLAN' THEN 'connection_plan'
                      ELSE t.val
                    END
                  )
                  ORDER BY t.ord
                )
                FROM jsonb_array_elements_text(
                  COALESCE(o.missing_params, '[]'::jsonb)
                ) WITH ORDINALITY AS t(val, ord)
              ),
              '[]'::jsonb
            )
            WHERE o.missing_params IS NOT NULL
              AND (
                o.missing_params @> '["BALANCE_ACT"]'::jsonb
                OR o.missing_params @> '["CONNECTION_PLAN"]'::jsonb
              );
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        text(
            """
            UPDATE orders o
            SET missing_params = COALESCE(
              (
                SELECT jsonb_agg(
                  to_jsonb(
                    CASE t.val
                      WHEN 'balance_act' THEN 'BALANCE_ACT'
                      WHEN 'connection_plan' THEN 'CONNECTION_PLAN'
                      ELSE t.val
                    END
                  )
                  ORDER BY t.ord
                )
                FROM jsonb_array_elements_text(
                  COALESCE(o.missing_params, '[]'::jsonb)
                ) WITH ORDINALITY AS t(val, ord)
              ),
              '[]'::jsonb
            )
            WHERE o.missing_params IS NOT NULL
              AND (
                o.missing_params @> '["balance_act"]'::jsonb
                OR o.missing_params @> '["connection_plan"]'::jsonb
              );
            """
        )
    )
