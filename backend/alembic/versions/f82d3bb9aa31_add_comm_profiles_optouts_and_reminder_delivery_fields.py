"""add_comm_profiles_optouts_and_reminder_delivery_fields

Revision ID: f82d3bb9aa31
Revises: c13f2a9d0f20
Create Date: 2026-04-06 22:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f82d3bb9aa31"
down_revision: Union[str, Sequence[str], None] = "c13f2a9d0f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())

    if "reminders" in table_names:
        cols = {c["name"] for c in inspector.get_columns("reminders")}
        if "delivered_at" not in cols:
            op.add_column("reminders", sa.Column("delivered_at", sa.DateTime(), nullable=True))
        if "responded_at" not in cols:
            op.add_column("reminders", sa.Column("responded_at", sa.DateTime(), nullable=True))
        if "external_message_id" not in cols:
            op.add_column("reminders", sa.Column("external_message_id", sa.String(), nullable=True))

    if "communication_tenant_profiles" not in table_names:
        op.create_table(
            "communication_tenant_profiles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("active", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("twilio_account_sid", sa.String(), nullable=True),
            sa.Column("twilio_auth_token", sa.String(), nullable=True),
            sa.Column("twilio_messaging_service_sid", sa.String(), nullable=True),
            sa.Column("twilio_phone_number", sa.String(), nullable=True),
            sa.Column("retell_agent_id", sa.String(), nullable=True),
            sa.Column("retell_phone_number", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id"),
        )
        op.create_index(
            op.f("ix_communication_tenant_profiles_id"),
            "communication_tenant_profiles",
            ["id"],
            unique=False,
        )

    if "sms_opt_outs" not in table_names:
        op.create_table(
            "sms_opt_outs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("phone", sa.String(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_sms_opt_outs_id"), "sms_opt_outs", ["id"], unique=False)
        op.create_index(op.f("ix_sms_opt_outs_phone"), "sms_opt_outs", ["phone"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())

    if "sms_opt_outs" in table_names:
        idx = {i["name"] for i in inspector.get_indexes("sms_opt_outs")}
        for name in [op.f("ix_sms_opt_outs_phone"), op.f("ix_sms_opt_outs_id")]:
            if name in idx:
                op.drop_index(name, table_name="sms_opt_outs")
        op.drop_table("sms_opt_outs")

    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())
    if "communication_tenant_profiles" in table_names:
        idx = {i["name"] for i in inspector.get_indexes("communication_tenant_profiles")}
        name = op.f("ix_communication_tenant_profiles_id")
        if name in idx:
            op.drop_index(name, table_name="communication_tenant_profiles")
        op.drop_table("communication_tenant_profiles")

    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())
    if "reminders" in table_names:
        cols = {c["name"] for c in inspector.get_columns("reminders")}
        if "external_message_id" in cols:
            op.drop_column("reminders", "external_message_id")
        if "responded_at" in cols:
            op.drop_column("reminders", "responded_at")
        if "delivered_at" in cols:
            op.drop_column("reminders", "delivered_at")
