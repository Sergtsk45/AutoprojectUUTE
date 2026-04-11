"""add calculator_configs table

Revision ID: 20260412_uute_calc_configs
Revises: 20260411_uute_object_city
Create Date: 2026-04-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision: str = "20260412_uute_calc_configs"
down_revision: Union[str, None] = "20260411_uute_object_city"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "calculator_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", UUID(as_uuid=True), nullable=False),
        sa.Column("calculator_type", sa.String(length=50), nullable=False),
        sa.Column("config_data", JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("total_params", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("filled_params", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missing_required", JSONB(), nullable=False, server_default="[]"),
        sa.Column("client_requested_params", JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index(
        op.f("ix_calculator_configs_order_id"),
        "calculator_configs",
        ["order_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_calculator_configs_order_id"), table_name="calculator_configs"
    )
    op.drop_table("calculator_configs")
