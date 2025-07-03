"""add attempts column to email_verifications

Revision ID: 0e52c63a3730
Revises: aba7357c6aab
Create Date: 2025-07-03 07:41:08.860505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e52c63a3730'
down_revision: Union[str, Sequence[str], None] = 'aba7357c6aab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('email_verifications') as batch_op:
        batch_op.add_column(sa.Column('attempts', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    """
    Downgrade schema.
    """
    with op.batch_alter_table('email_verifications') as batch_op:
        batch_op.drop_column('attempts')
