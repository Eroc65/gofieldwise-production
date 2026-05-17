"""add connect settings

Revision ID: e2f6a9c1d4b8
Revises: d4c8b7a9f101
Create Date: 2026-05-17 04:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e2f6a9c1d4b8"
down_revision = "d4c8b7a9f101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())

    if "connect_settings" not in table_names:
        op.create_table(
            "connect_settings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("settings_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id"),
        )
        op.create_index(op.f("ix_connect_settings_id"), "connect_settings", ["id"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())

    if "connect_settings" in table_names:
        indexes = {idx["name"] for idx in inspector.get_indexes("connect_settings")}
        index_name = op.f("ix_connect_settings_id")
        if index_name in indexes:
            op.drop_index(index_name, table_name="connect_settings")
        op.drop_table("connect_settings")
