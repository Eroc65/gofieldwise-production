"""add invoice lifecycle fields

Revision ID: 7eba593436e3
Revises: f19e56db4bf6
Create Date: 2026-04-01 11:35:22.236437

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7eba593436e3'
down_revision: Union[str, Sequence[str], None] = 'f19e56db4bf6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('invoices'):
        return

    existing_columns = {col['name'] for col in inspector.get_columns('invoices')}
    if 'issued_at' not in existing_columns:
        op.add_column('invoices', sa.Column('issued_at', sa.DateTime(), nullable=False))
    if 'due_at' not in existing_columns:
        op.add_column('invoices', sa.Column('due_at', sa.DateTime(), nullable=True))
    if 'paid_at' not in existing_columns:
        op.add_column('invoices', sa.Column('paid_at', sa.DateTime(), nullable=True))

    existing_indexes = {idx['name'] for idx in inspector.get_indexes('invoices')}
    due_at_index = op.f('ix_invoices_due_at')
    if due_at_index not in existing_indexes:
        op.create_index(due_at_index, 'invoices', ['due_at'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('invoices'):
        return

    existing_indexes = {idx['name'] for idx in inspector.get_indexes('invoices')}
    due_at_index = op.f('ix_invoices_due_at')
    if due_at_index in existing_indexes:
        op.drop_index(due_at_index, table_name='invoices')

    existing_columns = {col['name'] for col in inspector.get_columns('invoices')}
    if 'paid_at' in existing_columns:
        op.drop_column('invoices', 'paid_at')
    if 'due_at' in existing_columns:
        op.drop_column('invoices', 'due_at')
    if 'issued_at' in existing_columns:
        op.drop_column('invoices', 'issued_at')
