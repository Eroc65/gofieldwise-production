"""add admin portal auth tables

Revision ID: d4c8b7a9f101
Revises: c9d2e4f6a1b3
Create Date: 2026-05-17 04:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d4c8b7a9f101"
down_revision = "c9d2e4f6a1b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_credentials_id"), "admin_credentials", ["id"], unique=False)
    op.create_index(op.f("ix_admin_credentials_username"), "admin_credentials", ["username"], unique=True)

    op.create_table(
        "admin_password_resets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_password_resets_id"), "admin_password_resets", ["id"], unique=False)
    op.create_index(op.f("ix_admin_password_resets_token_hash"), "admin_password_resets", ["token_hash"], unique=True)
    op.create_index(op.f("ix_admin_password_resets_username"), "admin_password_resets", ["username"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_password_resets_username"), table_name="admin_password_resets")
    op.drop_index(op.f("ix_admin_password_resets_token_hash"), table_name="admin_password_resets")
    op.drop_index(op.f("ix_admin_password_resets_id"), table_name="admin_password_resets")
    op.drop_table("admin_password_resets")

    op.drop_index(op.f("ix_admin_credentials_username"), table_name="admin_credentials")
    op.drop_index(op.f("ix_admin_credentials_id"), table_name="admin_credentials")
    op.drop_table("admin_credentials")
