"""add_organization_intake_key

Revision ID: 6c1a7f94b2de
Revises: 2f4c9f73a8b1
Create Date: 2026-04-05 02:15:00.000000

"""
from secrets import token_urlsafe
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6c1a7f94b2de"
down_revision: Union[str, Sequence[str], None] = "2f4c9f73a8b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def _new_intake_key() -> str:
    return f"org_{token_urlsafe(12)}"



def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    tables = set(inspector.get_table_names())
    if "organizations" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("organizations")}
    if "intake_key" not in columns:
        op.add_column("organizations", sa.Column("intake_key", sa.String(), nullable=True))

    rows = connection.execute(sa.text("SELECT id FROM organizations WHERE intake_key IS NULL OR intake_key = ''")).fetchall()
    for row in rows:
        org_id = int(row[0])
        connection.execute(
            sa.text("UPDATE organizations SET intake_key = :key WHERE id = :org_id"),
            {"key": _new_intake_key(), "org_id": org_id},
        )

    indexes = {index["name"] for index in inspector.get_indexes("organizations")}
    index_name = "ix_organizations_intake_key"
    if index_name not in indexes:
        op.create_index(index_name, "organizations", ["intake_key"], unique=True)



def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    tables = set(inspector.get_table_names())
    if "organizations" not in tables:
        return

    indexes = {index["name"] for index in inspector.get_indexes("organizations")}
    index_name = "ix_organizations_intake_key"
    if index_name in indexes:
        op.drop_index(index_name, table_name="organizations")

    columns = {column["name"] for column in inspector.get_columns("organizations")}
    if "intake_key" in columns:
        op.drop_column("organizations", "intake_key")
