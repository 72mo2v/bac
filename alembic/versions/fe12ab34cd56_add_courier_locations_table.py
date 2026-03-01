"""Add courier locations table

Revision ID: fe12ab34cd56
Revises: c1b2a3d4e5f6
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fe12ab34cd56"
down_revision: Union[str, Sequence[str], None] = "c1b2a3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "courier_locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("courier_user_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("heading", sa.Float(), nullable=True),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["courier_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_courier_locations_id", "courier_locations", ["id"], unique=False)
    op.create_index("ix_courier_locations_courier_user_id", "courier_locations", ["courier_user_id"], unique=False)
    op.create_index("ix_courier_locations_order_id", "courier_locations", ["order_id"], unique=False)
    op.create_index("ix_courier_locations_created_at", "courier_locations", ["created_at"], unique=False)
    op.create_index(
        "ix_courier_locations_courier_created_at",
        "courier_locations",
        ["courier_user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_courier_locations_courier_created_at", table_name="courier_locations")
    op.drop_index("ix_courier_locations_created_at", table_name="courier_locations")
    op.drop_index("ix_courier_locations_order_id", table_name="courier_locations")
    op.drop_index("ix_courier_locations_courier_user_id", table_name="courier_locations")
    op.drop_index("ix_courier_locations_id", table_name="courier_locations")
    op.drop_table("courier_locations")

