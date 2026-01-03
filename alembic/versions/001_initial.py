"""Initial migration - create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('file_size', sa.Float(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('page_count', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', 'needs_review', name='documentstatus'), nullable=False),
        sa.Column('document_type', sa.Enum('invoice', 'receipt', 'medical', 'legal', 'financial', 'identity', 'correspondence', 'unknown', name='documenttype'), nullable=True),
        sa.Column('classification_confidence', sa.Float(), nullable=True),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('text_search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('upload_timestamp', sa.DateTime(), nullable=False),
        sa.Column('processing_started_at', sa.DateTime(), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Float(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for documents
    op.create_index('idx_documents_status', 'documents', ['status'])
    op.create_index('idx_documents_type', 'documents', ['document_type'])
    op.create_index('idx_documents_upload_timestamp', 'documents', ['upload_timestamp'])
    op.create_index('idx_documents_text_search', 'documents', ['text_search_vector'], postgresql_using='gin')

    # Create extracted_metadata table
    op.create_table(
        'extracted_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.String(50), nullable=True),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('extraction_model', sa.String(100), nullable=True),
        sa.Column('extraction_confidence', sa.Float(), nullable=True),
        sa.Column('extraction_timestamp', sa.DateTime(), nullable=True),
        sa.Column('is_validated', sa.Float(), nullable=True, default=0),
        sa.Column('validated_by', sa.String(100), nullable=True),
        sa.Column('validated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id')
    )
    
    # Create indexes for extracted_metadata
    op.create_index('idx_metadata_document_type', 'extracted_metadata', ['document_type'])
    op.create_index('idx_metadata_data', 'extracted_metadata', ['data'], postgresql_using='gin')

    # Create ocr_results table
    op.create_table(
        'ocr_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_number', sa.Float(), nullable=False, default=1),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('bounding_box', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('sequence_order', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for ocr_results
    op.create_index('idx_ocr_document_page', 'ocr_results', ['document_id', 'page_number'])

    # Create processing_queue table
    op.create_table(
        'processing_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('priority', sa.Float(), nullable=False, default=5),
        sa.Column('queued_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for processing_queue
    op.create_index('idx_queue_priority', 'processing_queue', ['priority', 'queued_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('processing_queue')
    op.drop_table('ocr_results')
    op.drop_table('extracted_metadata')
    op.drop_table('documents')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS documentstatus')
    op.execute('DROP TYPE IF EXISTS documenttype')
