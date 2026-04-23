"""Индексы для админского листинга и частых запросов файлов.

Фаза B3 аудита (2026-04-22). Добавляем три индекса под типичные запросы:

1. `ix_orders_created_at_desc` — `Order.created_at DESC` для сортировки
   списка заявок «по новизне» в админке (без фильтра по статусу).
2. `ix_orders_status_created_at_desc` — `(status, created_at DESC)` для
   листингов с фильтром по статусу (топ-кейс админки).
3. `ix_order_files_order_id_category` — `(order_id, category)` для частых
   запросов «файл заявки X категории Y» (`tu_files = [f for f in order.files
   if f.category.value == "tu"]` и аналогичные в `tasks.py`).

Все индексы создаются через `CREATE INDEX CONCURRENTLY IF NOT EXISTS` —
не блокирует таблицу в проде. Нужен `autocommit_block`, потому что
CONCURRENTLY не работает внутри транзакции.

EXPLAIN-сравнение типичного админского запроса (в проде после миграции):

  SELECT * FROM orders
  WHERE status = 'NEW'
  ORDER BY created_at DESC
  LIMIT 50;

  ── до:    Seq Scan on orders ... Sort
  ── после: Index Scan Backward using ix_orders_status_created_at_desc

Revision ID: 20260422_uute_listing_idx
Revises: 20260421_uute_fc_lower_missing
Create Date: 2026-04-22
"""

from alembic import op
from sqlalchemy import text

revision = "20260422_uute_listing_idx"
down_revision = "20260421_uute_fc_lower_missing"
branch_labels = None
depends_on = None


_INDEXES_UP = (
    # `created_at DESC` — для сортировки админского listing без фильтра.
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_orders_created_at_desc
        ON orders (created_at DESC);
    """,
    # `(status, created_at DESC)` — топ-запрос: листинг по статусу.
    # PostgreSQL btree поддерживает мульти-ключевую сортировку, и
    # `ORDER BY created_at DESC` будет использовать индекс backward-scan.
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_orders_status_created_at_desc
        ON orders (status, created_at DESC);
    """,
    # Файлы заявки по категории — частый запрос в `tasks.py` / `landing.py`.
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_order_files_order_id_category
        ON order_files (order_id, category);
    """,
)

_INDEXES_DOWN = (
    "DROP INDEX CONCURRENTLY IF EXISTS ix_order_files_order_id_category;",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_orders_status_created_at_desc;",
    "DROP INDEX CONCURRENTLY IF EXISTS ix_orders_created_at_desc;",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    with op.get_context().autocommit_block():
        for stmt in _INDEXES_UP:
            op.execute(text(stmt))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    with op.get_context().autocommit_block():
        for stmt in _INDEXES_DOWN:
            op.execute(text(stmt))
