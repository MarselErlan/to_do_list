"""add session and team management tables

Revision ID: aba7357c6aab
Revises: ea8302a249de
Create Date: 2025-07-03 06:58:29.679967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aba7357c6aab'
down_revision: Union[str, Sequence[str], None] = 'ea8302a249de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, index=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_table(
        'session_members',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, index=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', sa.String(), default='collaborator', nullable=False), # Roles: owner, collaborator
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('session_id', 'user_id', name='uq_session_user')
    )

    with op.batch_alter_table('todos') as batch_op:
        batch_op.add_column(sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id'), nullable=True))
        batch_op.add_column(sa.Column('is_private', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('todos') as batch_op:
        batch_op.drop_column('is_private')
        batch_op.drop_column('session_id')

    op.drop_table('session_members')
    op.drop_table('sessions')
