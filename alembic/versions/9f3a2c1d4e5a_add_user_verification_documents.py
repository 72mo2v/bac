"""add user verification documents

Revision ID: 9f3a2c1d4e5a
Revises: 8c1f2a9d7b3e
Create Date: 2026-02-01 00:05:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9f3a2c1d4e5a"
down_revision = "8c1f2a9d7b3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("id_card_url", sa.String(), nullable=True))
    op.add_column("users", sa.Column("store_front_photo_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "store_front_photo_url")
    op.drop_column("users", "id_card_url")
