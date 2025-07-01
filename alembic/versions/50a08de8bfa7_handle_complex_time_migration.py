"""Handle complex time migration

Revision ID: 50a08de8bfa7
Revises: 5196eedd33de
Create Date: 2025-07-01 14:15:20.898150

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50a08de8bfa7'
down_revision: Union[str, Sequence[str], None] = '5196eedd33de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns for date and created_at
    op.add_column('todos', sa.Column('start_date', sa.Date(), nullable=True))
    op.add_column('todos', sa.Column('end_date', sa.Date(), nullable=True))
    op.add_column('todos', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))

    # Add temporary columns for time
    op.add_column('todos', sa.Column('start_time_new', sa.Time(), nullable=True))
    op.add_column('todos', sa.Column('end_time_new', sa.Time(), nullable=True))

    # Copy and cast data from old timestamp columns to new date and time columns
    op.execute('UPDATE todos SET start_date = start_time::date, start_time_new = start_time::time')
    op.execute('UPDATE todos SET end_date = end_time::date, end_time_new = end_time::time')

    # Drop old timestamp columns
    op.drop_column('todos', 'start_time')
    op.drop_column('todos', 'end_time')

    # Rename new time columns
    op.alter_column('todos', 'start_time_new', new_column_name='start_time')
    op.alter_column('todos', 'end_time_new', new_column_name='end_time')


def downgrade() -> None:
    # This is a destructive downgrade and may result in data loss.
    # It's provided for completeness but should be used with caution.

    # Add back old timestamp columns
    op.add_column('todos', sa.Column('start_time', sa.DateTime(), nullable=True))
    op.add_column('todos', sa.Column('end_time', sa.DateTime(), nullable=True))

    # Copy data back from date and time columns
    op.execute("UPDATE todos SET start_time = (start_date + start_time)::timestamp")
    op.execute("UPDATE todos SET end_time = (end_date + end_time)::timestamp")

    # Drop new columns
    op.drop_column('todos', 'start_date')
    op.drop_column('todos', 'start_time')
    op.drop_column('todos', 'end_date')
    op.drop_column('todos', 'end_time')
    op.drop_column('todos', 'created_at')
