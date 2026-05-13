"""add org is_active

Revision ID: c9d2e4f6a1b3
Revises: a7c3e9d2b114
Create Date: 2026-05-12 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d2e4f6a1b3"
down_revision: Union[str, Sequence[str], None] = "a7c3e9d2b114"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = {col["name"] for col in inspector.get_columns("organizations")}
    if "is_active" not in columns:
        op.add_column(
            "organizations",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = {col["name"] for col in inspector.get_columns("organizations")}
    if "is_active" in columns:
        op.drop_column("organizations", "is_active")
