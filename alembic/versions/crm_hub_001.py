"""Add CRM Integration Hub tables.

Revision ID: crm_hub_001
Revises: 
Create Date: 2024-05-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'crm_hub_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create CRMConfiguration table
    op.create_table(
        'crm_configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('crm_provider', sa.Enum('housecall_pro', 'servicetitan', 'jobber', 'google_calendar', 'google_business_profile', 'zapier', 'custom_webhook', 'manual', name='crmprovider'), nullable=False),
        sa.Column('integration_mode', sa.Enum('native_api', 'oauth', 'zapier', 'webhook', 'manual', name='integrationmode'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('config_data', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('field_mapping', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('handoff_status', sa.Enum('pending_setup', 'ready', 'testing', 'live', 'paused', 'failed', name='handoffstatus'), nullable=False, server_default='pending_setup'),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('approved_by_user_id', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('last_test_at', sa.DateTime(), nullable=True),
        sa.Column('last_test_status', sa.String(length=50), nullable=True),
        sa.Column('test_lead_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('leads_synced_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_crm_configurations_organization_id'), 'crm_configurations', ['organization_id'], unique=False)
    op.create_index(op.f('ix_crm_configurations_crm_provider'), 'crm_configurations', ['crm_provider'], unique=False)

    # Create IntakeCapture table
    op.create_table(
        'intake_captures',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('crm_config_id', sa.Integer(), nullable=True),
        sa.Column('intake_type', sa.Enum('incoming_call', 'form_submission', 'chat', 'email', 'manual_entry', name='intaketype'), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('intake_timestamp', sa.DateTime(), nullable=False),
        sa.Column('caller_name', sa.String(length=255), nullable=True),
        sa.Column('caller_phone', sa.String(length=20), nullable=True),
        sa.Column('caller_email', sa.String(length=255), nullable=True),
        sa.Column('caller_address', sa.String(length=500), nullable=True),
        sa.Column('service_type', sa.String(length=255), nullable=True),
        sa.Column('service_description', sa.Text(), nullable=True),
        sa.Column('urgency_level', sa.String(length=50), nullable=True),
        sa.Column('preferred_time', sa.DateTime(), nullable=True),
        sa.Column('raw_transcript', sa.Text(), nullable=True),
        sa.Column('extracted_fields', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('missing_fields', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('ai_confidence', sa.Float(), nullable=True),
        sa.Column('is_processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['crm_config_id'], ['crm_configurations.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_intake_captures_organization_id'), 'intake_captures', ['organization_id'], unique=False)
    op.create_index(op.f('ix_intake_captures_intake_type'), 'intake_captures', ['intake_type'], unique=False)
    op.create_index(op.f('ix_intake_captures_intake_timestamp'), 'intake_captures', ['intake_timestamp'], unique=False)
    op.create_index('idx_organization_timestamp', 'intake_captures', ['organization_id', 'intake_timestamp'], unique=False)
    op.create_index('idx_organization_processed', 'intake_captures', ['organization_id', 'is_processed'], unique=False)

    # Create CRMHandoff table
    op.create_table(
        'crm_handoffs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('intake_id', sa.Integer(), nullable=False),
        sa.Column('crm_config_id', sa.Integer(), nullable=False),
        sa.Column('crm_provider', sa.Enum('housecall_pro', 'servicetitan', 'jobber', 'google_calendar', 'google_business_profile', 'zapier', 'custom_webhook', 'manual', name='crmprovider'), nullable=False),
        sa.Column('integration_mode', sa.Enum('native_api', 'oauth', 'zapier', 'webhook', 'manual', name='integrationmode'), nullable=False),
        sa.Column('crm_payload', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('crm_response', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('external_record_id', sa.String(length=255), nullable=True),
        sa.Column('external_record_url', sa.String(length=500), nullable=True),
        sa.Column('is_successful', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('handoff_method', sa.String(length=100), nullable=False),
        sa.Column('handled_by', sa.String(length=100), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['intake_id'], ['intake_captures.id'], ),
        sa.ForeignKeyConstraint(['crm_config_id'], ['crm_configurations.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_crm_handoffs_organization_id'), 'crm_handoffs', ['organization_id'], unique=False)
    op.create_index(op.f('ix_crm_handoffs_intake_id'), 'crm_handoffs', ['intake_id'], unique=False)
    op.create_index(op.f('ix_crm_handoffs_sent_at'), 'crm_handoffs', ['sent_at'], unique=False)
    op.create_index('idx_organization_crm', 'crm_handoffs', ['organization_id', 'crm_provider'], unique=False)

    # Create OnboardingProgress table
    op.create_table(
        'onboarding_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('crm_config_id', sa.Integer(), nullable=True),
        sa.Column('step_1_crm_selected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('step_2_integration_mode', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('step_3_credentials_provided', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('step_4_field_mapping', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('step_5_test_lead', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('step_6_approved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('step_7_live', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('current_step', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['crm_config_id'], ['crm_configurations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id'),
    )

    # Create IntegrationHubStatus table
    op.create_table(
        'integration_hub_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('total_crm_configs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active_configs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_intakes_captured', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_handoffs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_handoffs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_handoffs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_intake_at', sa.DateTime(), nullable=True),
        sa.Column('last_handoff_at', sa.DateTime(), nullable=True),
        sa.Column('last_error_at', sa.DateTime(), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id'),
    )


def downgrade() -> None:
    op.drop_table('integration_hub_status')
    op.drop_table('onboarding_progress')
    op.drop_table('crm_handoffs')
    op.drop_table('intake_captures')
    op.drop_table('crm_configurations')
    
    # Drop enums
    sa.Enum('housecall_pro', 'servicetitan', 'jobber', 'google_calendar', 'google_business_profile', 'zapier', 'custom_webhook', 'manual', name='crmprovider').drop(op.get_bind())
    sa.Enum('native_api', 'oauth', 'zapier', 'webhook', 'manual', name='integrationmode').drop(op.get_bind())
    sa.Enum('pending_setup', 'ready', 'testing', 'live', 'paused', 'failed', name='handoffstatus').drop(op.get_bind())
    sa.Enum('incoming_call', 'form_submission', 'chat', 'email', 'manual_entry', name='intaketype').drop(op.get_bind())
