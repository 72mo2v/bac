"""Add store working hours and return policy

Revision ID: f4c2a8e2c9d0
Revises: d3f2c9e7a1b4
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f4c2a8e2c9d0"
down_revision: Union[str, Sequence[str], None] = "d3f2c9e7a1b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("working_hours", sa.String(), nullable=True))
    op.add_column("stores", sa.Column("return_policy", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("stores", "return_policy")
    op.drop_column("stores", "working_hours")
