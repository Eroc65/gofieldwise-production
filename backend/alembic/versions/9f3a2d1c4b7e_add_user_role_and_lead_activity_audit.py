"""add_user_role_and_lead_activity_audit

Revision ID: 9f3a2d1c4b7e
Revises: 6c1a7f94b2de
Create Date: 2026-04-05 06:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f3a2d1c4b7e"
down_revision: Union[str, Sequence[str], None] = "6c1a7f94b2de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if "users" in tables:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "role" not in user_columns:
            op.add_column("users", sa.Column("role", sa.String(), nullable=True))
        connection.execute(sa.text("UPDATE users SET role = 'owner' WHERE role IS NULL OR role = ''"))

    if "lead_activities" not in tables and "leads" in tables:
        op.create_table(
            "lead_activities",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("from_status", sa.String(), nullable=True),
            sa.Column("to_status", sa.String(), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("lead_id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_lead_activities_id"), "lead_activities", ["id"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if "lead_activities" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("lead_activities")}
        index_name = op.f("ix_lead_activities_id")
        if index_name in indexes:
            op.drop_index(index_name, table_name="lead_activities")
        op.drop_table("lead_activities")

    if "users" in tables:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "role" in user_columns:
            op.drop_column("users", "role")
