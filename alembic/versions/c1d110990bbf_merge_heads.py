"""merge heads

Revision ID: c1d110990bbf
Revises: 0c6d8f1a2b3c, b7c4d1e2f3a4
Create Date: 2026-02-01 18:49:14.925383

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d110990bbf'
down_revision: Union[str, Sequence[str], None] = ('0c6d8f1a2b3c', 'b7c4d1e2f3a4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
