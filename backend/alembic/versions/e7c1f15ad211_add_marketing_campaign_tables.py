"""add_marketing_campaign_tables

Revision ID: e7c1f15ad211
Revises: b4d2c8f1a903
Create Date: 2026-04-06 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7c1f15ad211"
down_revision: Union[str, Sequence[str], None] = "b4d2c8f1a903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if "marketing_campaigns" not in tables:
        op.create_table(
            "marketing_campaigns",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("channel", sa.String(), nullable=False),
            sa.Column("template", sa.Text(), nullable=True),
            sa.Column("lookback_days", sa.Integer(), nullable=False),
            sa.Column("launched_at", sa.DateTime(), nullable=True),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_marketing_campaigns_id"), "marketing_campaigns", ["id"], unique=False)

    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
    if "marketing_campaign_recipients" not in tables:
        op.create_table(
            "marketing_campaign_recipients",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("campaign_id", sa.Integer(), nullable=False),
            sa.Column("customer_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("reminder_id", sa.Integer(), nullable=True),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("sent_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"]),
            sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
            sa.ForeignKeyConstraint(["reminder_id"], ["reminders.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_marketing_campaign_recipients_id"),
            "marketing_campaign_recipients",
            ["id"],
            unique=False,
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if "marketing_campaign_recipients" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("marketing_campaign_recipients")}
        index_name = op.f("ix_marketing_campaign_recipients_id")
        if index_name in indexes:
            op.drop_index(index_name, table_name="marketing_campaign_recipients")
        op.drop_table("marketing_campaign_recipients")

    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
    if "marketing_campaigns" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("marketing_campaigns")}
        index_name = op.f("ix_marketing_campaigns_id")
        if index_name in indexes:
            op.drop_index(index_name, table_name="marketing_campaigns")
        op.drop_table("marketing_campaigns")
