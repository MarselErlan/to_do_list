"""add is_global_public to todos table

Revision ID: 64520991b6c8
Revises: ccd6e2944184
Create Date: 2025-07-03 18:36:56.857408

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64520991b6c8'
down_revision: Union[str, Sequence[str], None] = 'ccd6e2944184'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('todos', sa.Column('is_global_public', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('todos', 'is_global_public')
