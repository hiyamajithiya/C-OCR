"""Add API key usage tracking and template scoping tables

Revision ID: add_api_key_usage_tables
Revises: add_correction_tables
Create Date: 2026-02-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_api_key_usage_tables'
down_revision: Union[str, None] = 'add_correction_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add restrict_to_templates column to api_keys
    op.add_column('api_keys', sa.Column('restrict_to_templates', sa.Boolean(), nullable=False, server_default='false'))

    # Create api_key_templates association table (many-to-many)
    op.create_table('api_key_templates',
        sa.Column('api_key_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('api_key_id', 'template_id')
    )

    # Create api_key_usage table for tracking individual API calls
    op.create_table('api_key_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_key_usage_id'), 'api_key_usage', ['id'], unique=False)
    op.create_index(op.f('ix_api_key_usage_api_key_id'), 'api_key_usage', ['api_key_id'], unique=False)
    op.create_index(op.f('ix_api_key_usage_tenant_id'), 'api_key_usage', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_api_key_usage_created_at'), 'api_key_usage', ['created_at'], unique=False)
    op.create_index(op.f('ix_api_key_usage_template_id'), 'api_key_usage', ['template_id'], unique=False)
    op.create_index(op.f('ix_api_key_usage_document_id'), 'api_key_usage', ['document_id'], unique=False)
    op.create_index('ix_api_key_usage_key_date', 'api_key_usage', ['api_key_id', 'created_at'], unique=False)
    op.create_index('ix_api_key_usage_tenant_date', 'api_key_usage', ['tenant_id', 'created_at'], unique=False)

    # Create api_key_daily_stats table for aggregated statistics
    op.create_table('api_key_daily_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('documents_accessed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('templates_accessed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('extractions_performed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_response_time_ms', sa.Integer(), nullable=True),
        sa.Column('max_response_time_ms', sa.Integer(), nullable=True),
        sa.Column('quota_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quota_limit', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('rate_limit_hits', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_key_daily_stats_id'), 'api_key_daily_stats', ['id'], unique=False)
    op.create_index(op.f('ix_api_key_daily_stats_api_key_id'), 'api_key_daily_stats', ['api_key_id'], unique=False)
    op.create_index(op.f('ix_api_key_daily_stats_tenant_id'), 'api_key_daily_stats', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_api_key_daily_stats_date'), 'api_key_daily_stats', ['date'], unique=False)
    op.create_index('ix_api_key_daily_stats_key_date', 'api_key_daily_stats', ['api_key_id', 'date'], unique=True)


def downgrade() -> None:
    # Drop api_key_daily_stats table
    op.drop_index('ix_api_key_daily_stats_key_date', table_name='api_key_daily_stats')
    op.drop_index(op.f('ix_api_key_daily_stats_date'), table_name='api_key_daily_stats')
    op.drop_index(op.f('ix_api_key_daily_stats_tenant_id'), table_name='api_key_daily_stats')
    op.drop_index(op.f('ix_api_key_daily_stats_api_key_id'), table_name='api_key_daily_stats')
    op.drop_index(op.f('ix_api_key_daily_stats_id'), table_name='api_key_daily_stats')
    op.drop_table('api_key_daily_stats')

    # Drop api_key_usage table
    op.drop_index('ix_api_key_usage_tenant_date', table_name='api_key_usage')
    op.drop_index('ix_api_key_usage_key_date', table_name='api_key_usage')
    op.drop_index(op.f('ix_api_key_usage_document_id'), table_name='api_key_usage')
    op.drop_index(op.f('ix_api_key_usage_template_id'), table_name='api_key_usage')
    op.drop_index(op.f('ix_api_key_usage_created_at'), table_name='api_key_usage')
    op.drop_index(op.f('ix_api_key_usage_tenant_id'), table_name='api_key_usage')
    op.drop_index(op.f('ix_api_key_usage_api_key_id'), table_name='api_key_usage')
    op.drop_index(op.f('ix_api_key_usage_id'), table_name='api_key_usage')
    op.drop_table('api_key_usage')

    # Drop api_key_templates association table
    op.drop_table('api_key_templates')

    # Remove restrict_to_templates column from api_keys
    op.drop_column('api_keys', 'restrict_to_templates')
