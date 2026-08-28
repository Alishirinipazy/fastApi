"""add tapin shipping fields to orders

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-08-22 00:00:00

Adds columns for the Tapin logistics integration: which shipping tier the
customer picked at checkout (tapin_order_type), and the results of
registering the order with Tapin after payment (tapin_order_id,
tapin_barcode, tapin_register_error). shipping_method_id was already
nullable in the initial schema, so no change needed there.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("tapin_order_type", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("tapin_order_id", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("tapin_barcode", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("tapin_register_error", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "tapin_register_error")
    op.drop_column("orders", "tapin_barcode")
    op.drop_column("orders", "tapin_order_id")
    op.drop_column("orders", "tapin_order_type")