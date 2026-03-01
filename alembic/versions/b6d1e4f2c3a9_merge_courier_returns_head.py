"""Merge courier returns head

Revision ID: b6d1e4f2c3a9
Revises: c1d110990bbf, a7c9b3d1e2f4
Create Date: 2026-02-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6d1e4f2c3a9"
down_revision: Union[str, Sequence[str], None] = ("c1d110990bbf", "a7c9b3d1e2f4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

