"""add_marketing_image_campaign_packs_table

Revision ID: a7c3e9d2b114
Revises: f82d3bb9aa31
Create Date: 2026-04-07 20:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c3e9d2b114"
down_revision: Union[str, Sequence[str], None] = "f82d3bb9aa31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())

    if "marketing_image_campaign_packs" not in table_names:
        op.create_table(
            "marketing_image_campaign_packs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=False, server_default="Custom saved preset"),
            sa.Column("template_code", sa.String(), nullable=False, server_default="social_promo"),
            sa.Column("channel_code", sa.String(), nullable=False, server_default="instagram_feed"),
            sa.Column("trade_code", sa.String(), nullable=False, server_default="general_home_services"),
            sa.Column("service_type", sa.String(), nullable=False),
            sa.Column("offer_text", sa.String(), nullable=False),
            sa.Column("cta_text", sa.String(), nullable=False),
            sa.Column("primary_color", sa.String(), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_marketing_image_campaign_packs_id"), "marketing_image_campaign_packs", ["id"], unique=False)
        op.create_index(op.f("ix_marketing_image_campaign_packs_code"), "marketing_image_campaign_packs", ["code"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())

    if "marketing_image_campaign_packs" in table_names:
        indexes = {i["name"] for i in inspector.get_indexes("marketing_image_campaign_packs")}
        idx_id = op.f("ix_marketing_image_campaign_packs_id")
        idx_code = op.f("ix_marketing_image_campaign_packs_code")
        if idx_code in indexes:
            op.drop_index(idx_code, table_name="marketing_image_campaign_packs")
        if idx_id in indexes:
            op.drop_index(idx_id, table_name="marketing_image_campaign_packs")
        op.drop_table("marketing_image_campaign_packs")
