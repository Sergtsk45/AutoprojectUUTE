"""20260415_uute_advance_payment_model

Revision ID: 87fcef6f52ff
Revises: 20260412_uute_calc_configs
Create Date: 2026-04-14 21:02:54.094021
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '87fcef6f52ff'
down_revision: Union[str, None] = '20260412_uute_calc_configs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. Добавить значения в существующий enum order_status ---
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'AWAITING_CONTRACT'")
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'CONTRACT_SENT'")
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'ADVANCE_PAID'")
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'AWAITING_FINAL_PAYMENT'")

    # --- 2. Добавить значения в существующий enum file_category ---
    op.execute("ALTER TYPE file_category ADD VALUE IF NOT EXISTS 'COMPANY_CARD'")
    op.execute("ALTER TYPE file_category ADD VALUE IF NOT EXISTS 'CONTRACT'")
    op.execute("ALTER TYPE file_category ADD VALUE IF NOT EXISTS 'INVOICE'")
    op.execute("ALTER TYPE file_category ADD VALUE IF NOT EXISTS 'RSO_SCAN'")

    # --- 3. Добавить значения в существующий enum email_type ---
    op.execute("ALTER TYPE email_type ADD VALUE IF NOT EXISTS 'PROJECT_READY_PAYMENT'")
    op.execute("ALTER TYPE email_type ADD VALUE IF NOT EXISTS 'CONTRACT_DELIVERY'")
    op.execute("ALTER TYPE email_type ADD VALUE IF NOT EXISTS 'ADVANCE_RECEIVED'")
    op.execute("ALTER TYPE email_type ADD VALUE IF NOT EXISTS 'FINAL_PAYMENT_REQUEST'")
    op.execute("ALTER TYPE email_type ADD VALUE IF NOT EXISTS 'FINAL_PAYMENT_RECEIVED'")

    # --- 4. Создать новый enum payment_method ---
    payment_method_enum = sa.Enum('bank_transfer', 'online_card', name='payment_method')
    payment_method_enum.create(op.get_bind(), checkfirst=True)

    # --- 5. Новые колонки в таблице orders ---
    op.add_column('orders', sa.Column(
        'payment_method',
        sa.Enum('bank_transfer', 'online_card', name='payment_method'),
        nullable=True
    ))
    op.add_column('orders', sa.Column('payment_amount', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('advance_amount', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column(
        'advance_paid_at',
        sa.DateTime(timezone=True),
        nullable=True
    ))
    op.add_column('orders', sa.Column(
        'final_paid_at',
        sa.DateTime(timezone=True),
        nullable=True
    ))
    op.add_column('orders', sa.Column('company_requisites', postgresql.JSONB(), nullable=True))
    op.add_column('orders', sa.Column('contract_number', sa.String(length=100), nullable=True))

    # --- 6. calculator_configs: autogenerate ---
    op.drop_constraint('calculator_configs_order_id_key', 'calculator_configs', type_='unique')
    op.drop_index('ix_calculator_configs_order_id', table_name='calculator_configs')
    op.create_index(op.f('ix_calculator_configs_order_id'), 'calculator_configs', ['order_id'], unique=True)


def downgrade() -> None:
    # --- 6. calculator_configs: обратно ---
    op.drop_index(op.f('ix_calculator_configs_order_id'), table_name='calculator_configs')
    op.create_index('ix_calculator_configs_order_id', 'calculator_configs', ['order_id'], unique=False)
    op.create_unique_constraint('calculator_configs_order_id_key', 'calculator_configs', ['order_id'])

    # --- 5. Удалить колонки из orders ---
    op.drop_column('orders', 'contract_number')
    op.drop_column('orders', 'company_requisites')
    op.drop_column('orders', 'final_paid_at')
    op.drop_column('orders', 'advance_paid_at')
    op.drop_column('orders', 'advance_amount')
    op.drop_column('orders', 'payment_amount')
    op.drop_column('orders', 'payment_method')

    # --- 4. Удалить enum payment_method ---
    op.execute("DROP TYPE IF EXISTS payment_method")

    # Примечание: ALTER TYPE ... DROP VALUE не поддерживается в PostgreSQL,
    # поэтому значения order_status, file_category, email_type не откатываются.
