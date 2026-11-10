"""in-store (POS / card reader) sales

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-11-08 00:00:00

An in-store sale has no delivery address, so orders.address_id becomes
nullable. New columns record where the sale happened (sales_channel:
'online' | 'pos'), how it was paid (payment_method: 'gateway' | 'pos'),
the card-reader receipt reference the cashier typed in, and who rang it up.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("orders", "address_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("orders", sa.Column("sales_channel", sa.String(length=16), nullable=False, server_default="online"))
    op.add_column("orders", sa.Column("payment_method", sa.String(length=16), nullable=False, server_default="gateway"))
    op.add_column("orders", sa.Column("pos_reference", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("cashier_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "cashier_id")
    op.drop_column("orders", "pos_reference")
    op.drop_column("orders", "payment_method")
    op.drop_column("orders", "sales_channel")
    # address_id stays nullable: rolling it back would fail if in-store orders exist.
