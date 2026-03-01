"""add push tokens

Revision ID: fd8c34856348
Revises: b6d1e4f2c3a9
Create Date: 2026-02-10 18:17:18.612204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd8c34856348'
down_revision: Union[str, Sequence[str], None] = 'b6d1e4f2c3a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'push_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.Text(), nullable=False),
        sa.Column('platform', sa.String(length=20), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'token', name='uq_push_tokens_user_token'),
    )
    op.create_index(op.f('ix_push_tokens_id'), 'push_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_push_tokens_user_id'), 'push_tokens', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_push_tokens_user_id'), table_name='push_tokens')
    op.drop_index(op.f('ix_push_tokens_id'), table_name='push_tokens')
    op.drop_table('push_tokens')
