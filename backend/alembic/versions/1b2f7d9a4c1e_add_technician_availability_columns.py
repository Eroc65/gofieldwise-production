"""add_technician_availability_columns

Revision ID: 1b2f7d9a4c1e
Revises: de804b203707
Create Date: 2026-04-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1b2f7d9a4c1e"
down_revision: Union[str, Sequence[str], None] = "de804b203707"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not inspector.has_table("technicians"):
        return
    existing = {column["name"] for column in inspector.get_columns("technicians")}

    if "availability_start_hour_utc" not in existing:
        op.add_column(
            "technicians",
            sa.Column("availability_start_hour_utc", sa.Integer(), nullable=False, server_default=sa.text("8")),
        )
    if "availability_end_hour_utc" not in existing:
        op.add_column(
            "technicians",
            sa.Column("availability_end_hour_utc", sa.Integer(), nullable=False, server_default=sa.text("19")),
        )
    if "availability_weekdays" not in existing:
        op.add_column(
            "technicians",
            sa.Column(
                "availability_weekdays",
                sa.String(),
                nullable=False,
                server_default=sa.text("'0,1,2,3,4'"),
            ),
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not inspector.has_table("technicians"):
        return
    existing = {column["name"] for column in inspector.get_columns("technicians")}

    if "availability_weekdays" in existing:
        op.drop_column("technicians", "availability_weekdays")
    if "availability_end_hour_utc" in existing:
        op.drop_column("technicians", "availability_end_hour_utc")
    if "availability_start_hour_utc" in existing:
        op.drop_column("technicians", "availability_start_hour_utc")
