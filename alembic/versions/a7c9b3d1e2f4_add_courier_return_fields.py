"""Add courier return assignment fields

Revision ID: a7c9b3d1e2f4
Revises: fe12ab34cd56
Create Date: 2026-02-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c9b3d1e2f4"
down_revision: Union[str, Sequence[str], None] = "fe12ab34cd56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    courier_status_enum = sa.Enum(
        "ASSIGNED",
        "PICKED_UP",
        "DROPPED_OFF",
        name="courierreturnstatus",
    )
    courier_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("return_requests", sa.Column("courier_user_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_return_requests_courier_user_id"), "return_requests", ["courier_user_id"], unique=False)
    op.create_foreign_key(
        "fk_return_requests_courier_user_id_users",
        "return_requests",
        "users",
        ["courier_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("return_requests", sa.Column("courier_status", courier_status_enum, nullable=True))
    op.create_index(op.f("ix_return_requests_courier_status"), "return_requests", ["courier_status"], unique=False)

    op.add_column("return_requests", sa.Column("picked_up_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("return_requests", sa.Column("dropped_off_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("return_requests", sa.Column("courier_notes", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("return_requests", "courier_notes")
    op.drop_column("return_requests", "dropped_off_at")
    op.drop_column("return_requests", "picked_up_at")

    op.drop_index(op.f("ix_return_requests_courier_status"), table_name="return_requests")
    op.drop_column("return_requests", "courier_status")

    op.drop_constraint("fk_return_requests_courier_user_id_users", "return_requests", type_="foreignkey")
    op.drop_index(op.f("ix_return_requests_courier_user_id"), table_name="return_requests")
    op.drop_column("return_requests", "courier_user_id")

    courier_status_enum = sa.Enum(
        "ASSIGNED",
        "PICKED_UP",
        "DROPPED_OFF",
        name="courierreturnstatus",
    )
    courier_status_enum.drop(op.get_bind(), checkfirst=True)

