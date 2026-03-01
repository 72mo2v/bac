"""Add store page views daily

Revision ID: 8c1f2a9d7b3e
Revises: 6a258446c576
Create Date: 2026-01-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8c1f2a9d7b3e"
down_revision: Union[str, Sequence[str], None] = "6a258446c576"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_page_views_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("visits", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "day", name="uq_store_page_views_daily_store_day"),
    )
    op.create_index("ix_store_page_views_daily_id", "store_page_views_daily", ["id"])
    op.create_index("ix_store_page_views_daily_store_id", "store_page_views_daily", ["store_id"])
    op.create_index("ix_store_page_views_daily_day", "store_page_views_daily", ["day"])


def downgrade() -> None:
    op.drop_index("ix_store_page_views_daily_day", table_name="store_page_views_daily")
    op.drop_index("ix_store_page_views_daily_store_id", table_name="store_page_views_daily")
    op.drop_index("ix_store_page_views_daily_id", table_name="store_page_views_daily")
    op.drop_table("store_page_views_daily")
