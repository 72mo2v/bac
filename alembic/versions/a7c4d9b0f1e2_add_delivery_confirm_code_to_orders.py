"""add delivery_confirm_code to orders

Revision ID: a7c4d9b0f1e2
Revises: fe12ab34cd56
Create Date: 2026-02-11

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a7c4d9b0f1e2"
down_revision = "fe12ab34cd56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("delivery_confirm_code", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "delivery_confirm_code")

