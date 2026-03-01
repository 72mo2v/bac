"""Add category enhancements

Revision ID: 4d8d9f0f2d4b
Revises: 3f2c1c1a7b9a
Create Date: 2026-01-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d8d9f0f2d4b"
down_revision: Union[str, Sequence[str], None] = "3f2c1c1a7b9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.add_column("categories", sa.Column("display_order", sa.Integer(), nullable=True, server_default=sa.text("0")))
    op.add_column("categories", sa.Column("icon_url", sa.String(), nullable=True))
    op.add_column("categories", sa.Column("is_visible", sa.Boolean(), nullable=True, server_default=sa.text("true")))

    op.create_index(op.f("ix_categories_parent_id"), "categories", ["parent_id"], unique=False)
    op.create_foreign_key(
        "fk_categories_parent_id_categories",
        "categories",
        "categories",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_categories_parent_id_categories", "categories", type_="foreignkey")
    op.drop_index(op.f("ix_categories_parent_id"), table_name="categories")

    op.drop_column("categories", "is_visible")
    op.drop_column("categories", "icon_url")
    op.drop_column("categories", "display_order")
    op.drop_column("categories", "parent_id")
