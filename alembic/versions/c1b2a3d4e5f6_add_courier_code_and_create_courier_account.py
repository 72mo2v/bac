"""Add courier code and support creating courier accounts

Revision ID: c1b2a3d4e5f6
Revises: f4c2a8e2c9d0
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1b2a3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f4c2a8e2c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("couriers", sa.Column("courier_code", sa.String(), nullable=True))
    op.create_index("ix_couriers_courier_code", "couriers", ["courier_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_couriers_courier_code", table_name="couriers")
    op.drop_column("couriers", "courier_code")
