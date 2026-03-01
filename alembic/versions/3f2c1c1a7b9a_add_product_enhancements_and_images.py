"""Add product enhancements and images

Revision ID: 3f2c1c1a7b9a
Revises: 7ab1481deaec
Create Date: 2026-01-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f2c1c1a7b9a"
down_revision: Union[str, Sequence[str], None] = "7ab1481deaec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("is_deal", sa.Boolean(), nullable=True, server_default=sa.text("false")))
    op.add_column("products", sa.Column("is_bestseller", sa.Boolean(), nullable=True, server_default=sa.text("false")))
    op.add_column("products", sa.Column("is_featured", sa.Boolean(), nullable=True, server_default=sa.text("false")))
    op.add_column("products", sa.Column("deal_price", sa.Float(), nullable=True))
    op.add_column("products", sa.Column("deal_end_date", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "product_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_images_id"), "product_images", ["id"], unique=False)
    op.create_index(op.f("ix_product_images_product_id"), "product_images", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_product_images_product_id"), table_name="product_images")
    op.drop_index(op.f("ix_product_images_id"), table_name="product_images")
    op.drop_table("product_images")

    op.drop_column("products", "deal_end_date")
    op.drop_column("products", "deal_price")
    op.drop_column("products", "is_featured")
    op.drop_column("products", "is_bestseller")
    op.drop_column("products", "is_deal")
