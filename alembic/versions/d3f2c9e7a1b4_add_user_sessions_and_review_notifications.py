"""Add user sessions and review/notification fields

Revision ID: d3f2c9e7a1b4
Revises: 6e1b0f6d1c2a
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d3f2c9e7a1b4"
down_revision: Union[str, Sequence[str], None] = "6e1b0f6d1c2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_type", sa.String(), nullable=True),
        sa.Column("device_name", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("last_active", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_current", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])

    op.add_column("notifications", sa.Column("store_id", sa.Integer(), nullable=True))
    op.add_column("notifications", sa.Column("type", sa.String(length=50), nullable=True))
    op.create_index("ix_notifications_store_id", "notifications", ["store_id"])

    # Create product_reviews table first as it was missing from previous migrations
    op.create_table(
        "product_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_reviews_id", "product_reviews", ["id"])

    op.add_column("product_reviews", sa.Column("is_reported", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("product_reviews", sa.Column("report_reason", sa.Text(), nullable=True))
    op.add_column("product_reviews", sa.Column("reported_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_index("ix_notifications_store_id", table_name="notifications")
    op.drop_column("notifications", "type")
    op.drop_column("notifications", "store_id")

    op.drop_column("product_reviews", "reported_at")
    op.drop_column("product_reviews", "report_reason")
    op.drop_column("product_reviews", "is_reported")
    op.drop_index("ix_product_reviews_id", table_name="product_reviews")
    op.drop_table("product_reviews")

    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
