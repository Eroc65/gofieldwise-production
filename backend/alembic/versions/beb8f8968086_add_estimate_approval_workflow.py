"""add estimate approval workflow

Revision ID: beb8f8968086
Revises: 06861fea41fe
Create Date: 2026-04-01 12:26:10.481421

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'beb8f8968086'
down_revision: Union[str, Sequence[str], None] = '06861fea41fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('estimates'):
        return

    existing_columns = {col['name'] for col in inspector.get_columns('estimates')}
    if 'status' not in existing_columns:
        op.add_column('estimates', sa.Column('status', sa.String(), nullable=False))
    if 'issued_at' not in existing_columns:
        op.add_column('estimates', sa.Column('issued_at', sa.DateTime(), nullable=False))
    if 'approved_at' not in existing_columns:
        op.add_column('estimates', sa.Column('approved_at', sa.DateTime(), nullable=True))
    if 'rejected_at' not in existing_columns:
        op.add_column('estimates', sa.Column('rejected_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('estimates'):
        return

    existing_columns = {col['name'] for col in inspector.get_columns('estimates')}
    if 'rejected_at' in existing_columns:
        op.drop_column('estimates', 'rejected_at')
    if 'approved_at' in existing_columns:
        op.drop_column('estimates', 'approved_at')
    if 'issued_at' in existing_columns:
        op.drop_column('estimates', 'issued_at')
    if 'status' in existing_columns:
        op.drop_column('estimates', 'status')
