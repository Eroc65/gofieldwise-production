"""add_job_completion_workflow

Revision ID: d0bd3133fc90
Revises: beb8f8968086
Create Date: 2026-04-01 16:38:16.950904

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd0bd3133fc90'
down_revision: Union[str, Sequence[str], None] = 'beb8f8968086'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('jobs'):
        return

    existing_columns = {col['name'] for col in inspector.get_columns('jobs')}
    if 'completed_at' not in existing_columns:
        op.add_column('jobs', sa.Column('completed_at', sa.DateTime(), nullable=True))
    if 'completion_notes' not in existing_columns:
        op.add_column('jobs', sa.Column('completion_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('jobs'):
        return

    existing_columns = {col['name'] for col in inspector.get_columns('jobs')}
    if 'completion_notes' in existing_columns:
        op.drop_column('jobs', 'completion_notes')
    if 'completed_at' in existing_columns:
        op.drop_column('jobs', 'completed_at')
