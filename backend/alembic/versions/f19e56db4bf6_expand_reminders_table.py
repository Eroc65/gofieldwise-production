"""expand reminders table

Revision ID: f19e56db4bf6
Revises: 49c7f387b5ad
Create Date: 2026-04-01 11:05:09.525972

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f19e56db4bf6'
down_revision: Union[str, Sequence[str], None] = '49c7f387b5ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite does not support ALTER COLUMN, so we use batch mode to rebuild
    # the reminders table with the new schema.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table('reminders'):
        op.drop_table('reminders')
    op.create_table(
        'reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('channel', sa.String(), nullable=False, server_default='internal'),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('due_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('lead_id', sa.Integer(), nullable=True),
        sa.Column('job_id', sa.Integer(), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id']),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_reminders_due_at'), 'reminders', ['due_at'], unique=False)
    op.create_index(op.f('ix_reminders_id'), 'reminders', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reminders_id'), table_name='reminders')
    op.drop_index(op.f('ix_reminders_due_at'), table_name='reminders')
    op.drop_table('reminders')
    op.create_table(
        'reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('scheduled_time', sa.DateTime(), nullable=True),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
