"""add_payment_reminder_stage

Revision ID: de804b203707
Revises: d0bd3133fc90
Create Date: 2026-04-01 16:53:39.058081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'de804b203707'
down_revision: Union[str, Sequence[str], None] = 'd0bd3133fc90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('invoices'):
        return

    existing_columns = {col['name'] for col in inspector.get_columns('invoices')}
    if 'payment_reminder_stage' not in existing_columns:
        op.add_column('invoices', sa.Column('payment_reminder_stage', sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('invoices'):
        return

    existing_columns = {col['name'] for col in inspector.get_columns('invoices')}
    if 'payment_reminder_stage' in existing_columns:
        op.drop_column('invoices', 'payment_reminder_stage')
