"""merge advance_payment_model branch with 2026-04-16 signed-contract/rso branch

Revision ID: 20260420_uute_merge_advance_payment_heads
Revises: 87fcef6f52ff, 20260416_uute_tu_parsed_notification
Create Date: 2026-04-20

Контекст
--------
Исторически после `20260412_uute_calc_configs` в графе миграций возникло
ДВЕ головы:

  20260412_uute_calc_configs
    ├── 87fcef6f52ff                            (2026-04-14, прод-миграция,
    │                                            сгенерирована через
    │                                            `alembic revision --autogenerate`
    │                                            прямо на prod-сервере и только
    │                                            сейчас закоммичена в git)
    └── 20260416_uute_signed_contract_enums
          → 20260416_uute_final_payment_rso_feedback
          → 20260416_uute_rso_remarks_status
          → 20260416_uute_tu_parsed_notification  (2026-04-16, git-цепочка)

На prod `alembic_version` содержит ОБЕ строки — 87fcef6f52ff и
20260416_uute_tu_parsed_notification. Обе ветви физически применены
к БД; пересечений между ними нет (проверено в ходе восстановления
87fcef6f52ff).

Эта миграция — merge point: без операций DDL/DML, только сливает обе
головы в одну. После `alembic upgrade head` на prod две записи в
`alembic_version` заменяются одной — этой самой ревизией.
На clean-БД (CI/новый стенд) alembic пройдёт обе ветви независимо,
затем применит merge.
"""
from typing import Sequence, Union


revision: str = "20260420_uute_merge_advance_payment_heads"
down_revision: Union[str, Sequence[str], None] = (
    "87fcef6f52ff",
    "20260416_uute_tu_parsed_notification",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Чистый merge — ни DDL, ни DML. Всё уже в БД.
    pass


def downgrade() -> None:
    # Откат merge обратно в две головы не поддерживается в проде:
    # для штатного rollback пришлось бы downgrade-ить обе ветви параллельно,
    # что разрушило бы данные таблицы orders (drop advance_amount и т.п.).
    pass
