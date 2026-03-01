"""Merge heads and add product shipping fields

Revision ID: e3a9b1d2c4f7
Revises: 2aaf70f6434e, c1b2a3d4e5f6
Create Date: 2026-01-29

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3a9b1d2c4f7"
down_revision: Union[str, Sequence[str], None] = ("2aaf70f6434e", "c1b2a3d4e5f6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "is_free_shipping",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "shipping_fee",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("products", "shipping_fee")
    op.drop_column("products", "is_free_shipping")
