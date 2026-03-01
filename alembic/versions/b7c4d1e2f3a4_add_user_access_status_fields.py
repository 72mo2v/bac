"""Add user access status fields

Revision ID: b7c4d1e2f3a4
Revises: 9f3a2c1d4e5a
Create Date: 2026-02-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c4d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "9f3a2c1d4e5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    enum = sa.Enum("ACTIVE", "BLOCKED", "SUSPENDED", name="useraccessstatus")
    enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "users",
        sa.Column(
            "access_status",
            enum,
            nullable=False,
            server_default="ACTIVE",
        ),
    )
    op.add_column("users", sa.Column("access_reason", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("suspended_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "suspended_until")
    op.drop_column("users", "access_reason")
    op.drop_column("users", "access_status")

    # Drop enum type explicitly (Postgres). Safe on others.
    try:
        sa.Enum(name="useraccessstatus").drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass
