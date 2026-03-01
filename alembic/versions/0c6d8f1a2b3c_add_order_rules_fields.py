"""Add order rules fields

Revision ID: 0c6d8f1a2b3c
Revises: 9f3a2c1d4e5a
Create Date: 2026-02-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0c6d8f1a2b3c"
down_revision: Union[str, Sequence[str], None] = "9f3a2c1d4e5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("max_qty_per_order", sa.Integer(), nullable=True))

    op.add_column("stores", sa.Column("min_order_total", sa.Float(), nullable=True))
    op.add_column("stores", sa.Column("order_shipping_fee", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("stores", "order_shipping_fee")
    op.drop_column("stores", "min_order_total")

    op.drop_column("products", "max_qty_per_order")
