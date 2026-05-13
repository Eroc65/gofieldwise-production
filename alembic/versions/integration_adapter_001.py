"""Add integration tables for universal adapter.

Revision ID: integration_adapter_001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'integration_adapter_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create IntegrationConfig table
    op.create_table(
        'integration_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.Enum('zapier', 'google_sheets', 'jobber', 'housecall', 'custom_webhook', 'airtable', 'shopify', name='integrationplatform'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('direction', sa.Enum('inbound', 'outbound', 'bidirectional', name='integrationdirection'), nullable=False),
        sa.Column('config_data', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('field_mapping', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('webhook_url', sa.String(length=500), nullable=True),
        sa.Column('webhook_secret', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_status', sa.Enum('success', 'failed', 'pending', 'partial', name='syncstatus'), nullable=True),
        sa.Column('last_sync_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('webhook_url'),
    )
    op.create_index(op.f('ix_integration_configs_id'), 'integration_configs', ['id'], unique=False)
    op.create_index(op.f('ix_integration_configs_organization_id'), 'integration_configs', ['organization_id'], unique=False)
    op.create_index(op.f('ix_integration_configs_platform'), 'integration_configs', ['platform'], unique=False)

    # Create IntegrationSyncLog table
    op.create_table(
        'integration_sync_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('integration_config_id', sa.Integer(), nullable=False),
        sa.Column('sync_type', sa.String(length=50), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('gofieldwise_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('success', 'failed', 'pending', 'partial', name='syncstatus'), nullable=False),
        sa.Column('direction', sa.Enum('inbound', 'outbound', 'bidirectional', name='integrationdirection'), nullable=False),
        sa.Column('request_payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('response_payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['integration_config_id'], ['integration_configs.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_integration_sync_logs_id'), 'integration_sync_logs', ['id'], unique=False)
    op.create_index(op.f('ix_integration_sync_logs_integration_config_id'), 'integration_sync_logs', ['integration_config_id'], unique=False)
    op.create_index(op.f('ix_integration_sync_logs_created_at'), 'integration_sync_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('integration_sync_logs')
    op.drop_table('integration_configs')
    
    # Drop enums
    sa.Enum('success', 'failed', 'pending', 'partial', name='syncstatus').drop(op.get_bind())
    sa.Enum('inbound', 'outbound', 'bidirectional', name='integrationdirection').drop(op.get_bind())
    sa.Enum('zapier', 'google_sheets', 'jobber', 'housecall', 'custom_webhook', 'airtable', 'shopify', name='integrationplatform').drop(op.get_bind())
