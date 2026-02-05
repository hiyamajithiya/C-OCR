"""Add correction and learning tables

Revision ID: add_correction_tables
Revises: 3aacd8ba47aa
Create Date: 2026-02-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_correction_tables'
down_revision: Union[str, None] = '3aacd8ba47aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create extraction_corrections table
    op.create_table('extraction_corrections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('template_version_id', sa.Integer(), nullable=True),
        sa.Column('extraction_result_id', sa.Integer(), nullable=True),
        sa.Column('field_name', sa.String(length=255), nullable=False),
        sa.Column('field_label', sa.String(length=255), nullable=True),
        sa.Column('field_type', sa.String(length=50), nullable=True),
        sa.Column('original_value', sa.Text(), nullable=True),
        sa.Column('original_confidence', sa.Float(), nullable=True),
        sa.Column('extraction_method', sa.String(length=50), nullable=True),
        sa.Column('corrected_value', sa.Text(), nullable=False),
        sa.Column('correction_note', sa.Text(), nullable=True),
        sa.Column('is_processed', sa.Boolean(), nullable=False, default=False),
        sa.Column('learned_pattern', sa.JSON(), nullable=True),
        sa.Column('corrected_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['template_version_id'], ['template_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['extraction_result_id'], ['extraction_results.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['corrected_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_extraction_corrections_id'), 'extraction_corrections', ['id'], unique=False)
    op.create_index(op.f('ix_extraction_corrections_tenant_id'), 'extraction_corrections', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_extraction_corrections_document_id'), 'extraction_corrections', ['document_id'], unique=False)
    op.create_index(op.f('ix_extraction_corrections_template_id'), 'extraction_corrections', ['template_id'], unique=False)
    op.create_index(op.f('ix_extraction_corrections_field_name'), 'extraction_corrections', ['field_name'], unique=False)

    # Create field_abbreviations table
    op.create_table('field_abbreviations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('abbreviation', sa.String(length=50), nullable=False),
        sa.Column('expanded_form', sa.String(length=255), nullable=False),
        sa.Column('field_type', sa.String(length=50), nullable=True),
        sa.Column('doc_category', sa.String(length=100), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, default='manual'),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('success_count', sa.Integer(), nullable=False, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_field_abbreviations_id'), 'field_abbreviations', ['id'], unique=False)
    op.create_index(op.f('ix_field_abbreviations_tenant_id'), 'field_abbreviations', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_field_abbreviations_abbreviation'), 'field_abbreviations', ['abbreviation'], unique=False)

    # Create template_accuracy table
    op.create_table('template_accuracy',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('template_version_id', sa.Integer(), nullable=True),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('total_extractions', sa.Integer(), nullable=False, default=0),
        sa.Column('total_corrections', sa.Integer(), nullable=False, default=0),
        sa.Column('accuracy_rate', sa.Float(), nullable=True),
        sa.Column('avg_confidence', sa.Float(), nullable=True),
        sa.Column('field_metrics_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_version_id'], ['template_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_template_accuracy_id'), 'template_accuracy', ['id'], unique=False)
    op.create_index(op.f('ix_template_accuracy_tenant_id'), 'template_accuracy', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_template_accuracy_template_id'), 'template_accuracy', ['template_id'], unique=False)


def downgrade() -> None:
    # Drop template_accuracy table
    op.drop_index(op.f('ix_template_accuracy_template_id'), table_name='template_accuracy')
    op.drop_index(op.f('ix_template_accuracy_tenant_id'), table_name='template_accuracy')
    op.drop_index(op.f('ix_template_accuracy_id'), table_name='template_accuracy')
    op.drop_table('template_accuracy')

    # Drop field_abbreviations table
    op.drop_index(op.f('ix_field_abbreviations_abbreviation'), table_name='field_abbreviations')
    op.drop_index(op.f('ix_field_abbreviations_tenant_id'), table_name='field_abbreviations')
    op.drop_index(op.f('ix_field_abbreviations_id'), table_name='field_abbreviations')
    op.drop_table('field_abbreviations')

    # Drop extraction_corrections table
    op.drop_index(op.f('ix_extraction_corrections_field_name'), table_name='extraction_corrections')
    op.drop_index(op.f('ix_extraction_corrections_template_id'), table_name='extraction_corrections')
    op.drop_index(op.f('ix_extraction_corrections_document_id'), table_name='extraction_corrections')
    op.drop_index(op.f('ix_extraction_corrections_tenant_id'), table_name='extraction_corrections')
    op.drop_index(op.f('ix_extraction_corrections_id'), table_name='extraction_corrections')
    op.drop_table('extraction_corrections')
