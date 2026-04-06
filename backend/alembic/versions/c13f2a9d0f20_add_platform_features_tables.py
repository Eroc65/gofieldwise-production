"""add_platform_features_tables

Revision ID: c13f2a9d0f20
Revises: e7c1f15ad211
Create Date: 2026-04-06 21:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c13f2a9d0f20"
down_revision: Union[str, Sequence[str], None] = "e7c1f15ad211"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())

    if "organizations" in table_names:
        org_columns = {c["name"] for c in inspector.get_columns("organizations")}
        if "ai_guide_enabled" not in org_columns:
            op.add_column("organizations", sa.Column("ai_guide_enabled", sa.Integer(), nullable=False, server_default="0"))
        if "ai_guide_stage" not in org_columns:
            op.add_column("organizations", sa.Column("ai_guide_stage", sa.String(), nullable=False, server_default="off"))

    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())

    if "help_articles" not in table_names:
        op.create_table(
            "help_articles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("slug", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("category", sa.String(), nullable=False),
            sa.Column("context_key", sa.String(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_help_articles_id"), "help_articles", ["id"], unique=False)
        op.create_index(op.f("ix_help_articles_slug"), "help_articles", ["slug"], unique=False)

    if "coaching_snippets" not in table_names:
        op.create_table(
            "coaching_snippets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("trade", sa.String(), nullable=False),
            sa.Column("issue_pattern", sa.String(), nullable=False),
            sa.Column("senior_tip", sa.Text(), nullable=False),
            sa.Column("checklist", sa.Text(), nullable=True),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_coaching_snippets_id"), "coaching_snippets", ["id"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())

    if "coaching_snippets" in table_names:
        indexes = {i["name"] for i in inspector.get_indexes("coaching_snippets")}
        idx = op.f("ix_coaching_snippets_id")
        if idx in indexes:
            op.drop_index(idx, table_name="coaching_snippets")
        op.drop_table("coaching_snippets")

    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())
    if "help_articles" in table_names:
        indexes = {i["name"] for i in inspector.get_indexes("help_articles")}
        idx_id = op.f("ix_help_articles_id")
        idx_slug = op.f("ix_help_articles_slug")
        if idx_slug in indexes:
            op.drop_index(idx_slug, table_name="help_articles")
        if idx_id in indexes:
            op.drop_index(idx_id, table_name="help_articles")
        op.drop_table("help_articles")

    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())
    if "organizations" in table_names:
        org_columns = {c["name"] for c in inspector.get_columns("organizations")}
        if "ai_guide_stage" in org_columns:
            op.drop_column("organizations", "ai_guide_stage")
        if "ai_guide_enabled" in org_columns:
            op.drop_column("organizations", "ai_guide_enabled")
