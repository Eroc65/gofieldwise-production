"""add operator invites

Revision ID: b3f1d8c9a2e4
Revises: 86da21ff24c7
Create Date: 2026-05-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3f1d8c9a2e4"
down_revision: Union[str, Sequence[str], None] = "86da21ff24c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operator_invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("owner_name", sa.String(), nullable=True),
        sa.Column("business_name", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("setup_url", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(), nullable=True),
        sa.Column("redeemed_user_id", sa.Integer(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["redeemed_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operator_invites_id"), "operator_invites", ["id"], unique=False)
    op.create_index(op.f("ix_operator_invites_key_hash"), "operator_invites", ["key_hash"], unique=True)
    op.create_index(op.f("ix_operator_invites_email"), "operator_invites", ["email"], unique=False)
    op.create_index(op.f("ix_operator_invites_stripe_customer_id"), "operator_invites", ["stripe_customer_id"], unique=False)
    op.create_index(op.f("ix_operator_invites_stripe_subscription_id"), "operator_invites", ["stripe_subscription_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_operator_invites_stripe_subscription_id"), table_name="operator_invites")
    op.drop_index(op.f("ix_operator_invites_stripe_customer_id"), table_name="operator_invites")
    op.drop_index(op.f("ix_operator_invites_email"), table_name="operator_invites")
    op.drop_index(op.f("ix_operator_invites_key_hash"), table_name="operator_invites")
    op.drop_index(op.f("ix_operator_invites_id"), table_name="operator_invites")
    op.drop_table("operator_invites")
