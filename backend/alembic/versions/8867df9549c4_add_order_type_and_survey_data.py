"""add_order_type_and_survey_data

Revision ID: 8867df9549c4
Revises: 20260403_fc_upper
Create Date: 2026-04-03 11:37:36.343117

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '8867df9549c4'
down_revision: Union[str, None] = '20260403_fc_upper'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    order_type_enum = sa.Enum('express', 'standard', name='order_type')
    order_type_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('orders', sa.Column('order_type', order_type_enum, server_default='express', nullable=False))
    op.add_column('orders', sa.Column('survey_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'survey_data')
    op.drop_column('orders', 'order_type')
    sa.Enum(name='order_type').drop(op.get_bind(), checkfirst=True)
