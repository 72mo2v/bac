"""Add returns system

Revision ID: 6e1b0f6d1c2a
Revises: 4d8d9f0f2d4b
Create Date: 2026-01-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6e1b0f6d1c2a"
down_revision: Union[str, Sequence[str], None] = "4d8d9f0f2d4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "return_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "APPROVED", "REJECTED", name="returnstatus"), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_return_requests_id"), "return_requests", ["id"], unique=False)
    op.create_index(op.f("ix_return_requests_store_id"), "return_requests", ["store_id"], unique=False)
    op.create_index(op.f("ix_return_requests_order_id"), "return_requests", ["order_id"], unique=False)
    op.create_index(op.f("ix_return_requests_customer_id"), "return_requests", ["customer_id"], unique=False)
    op.create_index(op.f("ix_return_requests_status"), "return_requests", ["status"], unique=False)

    op.create_table(
        "return_proof_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("return_request_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["return_request_id"], ["return_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_return_proof_images_id"), "return_proof_images", ["id"], unique=False)
    op.create_index(op.f("ix_return_proof_images_return_request_id"), "return_proof_images", ["return_request_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_return_proof_images_return_request_id"), table_name="return_proof_images")
    op.drop_index(op.f("ix_return_proof_images_id"), table_name="return_proof_images")
    op.drop_table("return_proof_images")

    op.drop_index(op.f("ix_return_requests_status"), table_name="return_requests")
    op.drop_index(op.f("ix_return_requests_customer_id"), table_name="return_requests")
    op.drop_index(op.f("ix_return_requests_order_id"), table_name="return_requests")
    op.drop_index(op.f("ix_return_requests_store_id"), table_name="return_requests")
    op.drop_index(op.f("ix_return_requests_id"), table_name="return_requests")
    op.drop_table("return_requests")

    sa.Enum("PENDING", "APPROVED", "REJECTED", name="returnstatus").drop(op.get_bind(), checkfirst=True)
