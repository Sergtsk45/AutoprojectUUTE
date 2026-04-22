"""rename order_type enum value standard to custom

Revision ID: rename_standard_to_custom
Revises: 8867df9549c4
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'rename_standard_to_custom'
down_revision: Union[str, None] = '8867df9549c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE order_type RENAME VALUE 'standard' TO 'custom'")


def downgrade() -> None:
    op.execute("ALTER TYPE order_type RENAME VALUE 'custom' TO 'standard'")
