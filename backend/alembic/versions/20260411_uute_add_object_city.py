"""add object_city to orders

Revision ID: 20260411_uute_object_city
Revises: 20260407_uute_wci
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260411_uute_object_city"
down_revision: Union[str, None] = "20260407_uute_wci"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("object_city", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "object_city")
