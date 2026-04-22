"""Удаление legacy-статусов OrderStatus (C1/C2 аудита).

Фаза C1+C2 аудита (2026-04-22). Из enum `order_status` удаляются три
значения, отвечавшие старой цепочке «генерация проекта в T-FLEX →
инженер одобрил → платёж»:

* ``data_complete``
* ``generating_project``
* ``review``

Current flow больше их не использует: заявка идёт
``client_info_received → contract_sent → advance_paid → awaiting_final_payment
→ completed``. Три удаляемых статуса оставались в enum после рефакторинга
платёжной ветки, но тянули за собой 3 Celery-заглушки, legacy-ветки в
``approve_project`` / ``send_completed_project`` и «мусор» в UI админки и
лендинга. Подробный контекст — в ``docs/tasktracker.md`` (Задача C1/C2).

Что делает миграция:

1. **Backfill данных.** Любые заявки со «застрявшим» legacy-статусом
   переводятся в ``client_info_received`` — промежуточный «карантин»,
   откуда инженер вручную может перевести заявку куда нужно (см.
   ``ALLOWED_TRANSITIONS[CLIENT_INFO_RECEIVED]``).

   На момент миграции прод-данных с legacy-статусами нет (по
   состоянию 2026-04-22 все заявки проходят современный флоу), но
   UPDATE нужен, чтобы:
     - безопасно закрыть возможные dev/test-артефакты;
     - следующий шаг (смена типа колонки) не упал на «устаревшем»
       значении.

2. **Пересоздание типа PostgreSQL.** PostgreSQL не умеет убирать
   значения из enum в `ALTER TYPE` — используем классический приём:
     a) создаём новый тип ``order_status_new`` без legacy-значений,
     b) переводим ``orders.status`` на новый тип через явный cast
        ``status::text::order_status_new``,
     c) удаляем старый тип и переименовываем новый в ``order_status``.

3. **Downgrade.** Обратный путь: возвращаем три значения в enum и
   переводим столбец обратно. Никакого восстановления исходного
   статуса не делаем (для этого нет источника — колонки-аудита
   пользователь просил не добавлять).

Маппинг legacy → target:

+-----------------------+----------------------+
| Legacy                | Target               |
+=======================+======================+
| ``data_complete``     | ``client_info_received`` |
| ``generating_project``| ``client_info_received`` |
| ``review``            | ``client_info_received`` |
+-----------------------+----------------------+

Revision ID: 20260422_uute_drop_legacy_statuses
Revises: 20260422_uute_listing_idx
Create Date: 2026-04-22
"""

from alembic import op
from sqlalchemy import text

revision = "20260422_uute_drop_legacy_statuses"
down_revision = "20260422_uute_listing_idx"
branch_labels = None
depends_on = None


_LEGACY_STATUSES = ("data_complete", "generating_project", "review")
_TARGET_STATUS = "client_info_received"

# Полный набор значений enum *после* миграции (C2).
_NEW_ENUM_VALUES = (
    "new",
    "tu_parsing",
    "tu_parsed",
    "waiting_client_info",
    "client_info_received",
    "awaiting_contract",
    "contract_sent",
    "advance_paid",
    "awaiting_final_payment",
    "rso_remarks_received",
    "completed",
    "error",
)

# Полный набор значений enum *до* миграции (для downgrade).
_OLD_ENUM_VALUES = (
    "new",
    "tu_parsing",
    "tu_parsed",
    "waiting_client_info",
    "client_info_received",
    "data_complete",
    "generating_project",
    "review",
    "awaiting_contract",
    "contract_sent",
    "advance_paid",
    "awaiting_final_payment",
    "rso_remarks_received",
    "completed",
    "error",
)


def _format_enum_values(values: tuple[str, ...]) -> str:
    """Сформировать строку ``'a', 'b', 'c'`` для CREATE TYPE."""
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Backfill: закрываем возможные «зависшие» заявки.
    bind.execute(
        text(
            "UPDATE orders SET status = :target "
            "WHERE status::text = ANY(:legacy)"
        ),
        {"target": _TARGET_STATUS, "legacy": list(_LEGACY_STATUSES)},
    )

    # 2) Пересоздаём тип без legacy-значений.
    new_values_sql = _format_enum_values(_NEW_ENUM_VALUES)
    bind.execute(text(f"CREATE TYPE order_status_new AS ENUM ({new_values_sql})"))
    bind.execute(
        text(
            "ALTER TABLE orders "
            "ALTER COLUMN status TYPE order_status_new "
            "USING status::text::order_status_new"
        )
    )
    bind.execute(text("DROP TYPE order_status"))
    bind.execute(text("ALTER TYPE order_status_new RENAME TO order_status"))


def downgrade() -> None:
    bind = op.get_bind()

    # Обратный путь: возвращаем все 15 значений.
    old_values_sql = _format_enum_values(_OLD_ENUM_VALUES)
    bind.execute(text(f"CREATE TYPE order_status_old AS ENUM ({old_values_sql})"))
    bind.execute(
        text(
            "ALTER TABLE orders "
            "ALTER COLUMN status TYPE order_status_old "
            "USING status::text::order_status_old"
        )
    )
    bind.execute(text("DROP TYPE order_status"))
    bind.execute(text("ALTER TYPE order_status_old RENAME TO order_status"))
