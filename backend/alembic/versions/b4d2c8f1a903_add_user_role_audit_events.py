"""add_user_role_audit_events

Revision ID: b4d2c8f1a903
Revises: 9f3a2d1c4b7e
Create Date: 2026-04-05 07:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4d2c8f1a903"
down_revision: Union[str, Sequence[str], None] = "9f3a2d1c4b7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if "user_role_audit_events" not in tables:
        op.create_table(
            "user_role_audit_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=False),
            sa.Column("target_user_id", sa.Integer(), nullable=False),
            sa.Column("from_role", sa.String(), nullable=False),
            sa.Column("to_role", sa.String(), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["target_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_user_role_audit_events_id"), "user_role_audit_events", ["id"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if "user_role_audit_events" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("user_role_audit_events")}
        index_name = op.f("ix_user_role_audit_events_id")
        if index_name in indexes:
            op.drop_index(index_name, table_name="user_role_audit_events")
        op.drop_table("user_role_audit_events")
