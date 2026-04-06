"""add_job_lifecycle_timeline

Revision ID: 2f4c9f73a8b1
Revises: 1b2f7d9a4c1e
Create Date: 2026-04-05 01:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2f4c9f73a8b1"
down_revision: Union[str, Sequence[str], None] = "1b2f7d9a4c1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    job_columns = {column["name"] for column in inspector.get_columns("jobs")}
    if "on_my_way_at" not in job_columns:
        op.add_column("jobs", sa.Column("on_my_way_at", sa.DateTime(), nullable=True))
    if "started_at" not in job_columns:
        op.add_column("jobs", sa.Column("started_at", sa.DateTime(), nullable=True))

    tables = set(inspector.get_table_names())
    if "job_activities" not in tables:
        op.create_table(
            "job_activities",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("from_status", sa.String(), nullable=True),
            sa.Column("to_status", sa.String(), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("job_id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_job_activities_id"), "job_activities", ["id"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    tables = set(inspector.get_table_names())
    if "job_activities" in tables:
        op.drop_index(op.f("ix_job_activities_id"), table_name="job_activities")
        op.drop_table("job_activities")

    job_columns = {column["name"] for column in inspector.get_columns("jobs")}
    if "started_at" in job_columns:
        op.drop_column("jobs", "started_at")
    if "on_my_way_at" in job_columns:
        op.drop_column("jobs", "on_my_way_at")
