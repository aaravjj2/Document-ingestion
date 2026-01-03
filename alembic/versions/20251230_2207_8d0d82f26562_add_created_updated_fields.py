"""add_created_updated_fields

Revision ID: 8d0d82f26562
Revises: 82fb2032ae16
Create Date: 2025-12-30 22:07:17.575802

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8d0d82f26562"
down_revision: Union[str, None] = "82fb2032ae16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add created_at and updated_at to documents table
    op.add_column('documents', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')))
    op.add_column('documents', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')))
    
    # Set created_at to match upload_timestamp for existing records
    op.execute('UPDATE documents SET created_at = upload_timestamp WHERE created_at IS NULL')
    op.execute('UPDATE documents SET updated_at = upload_timestamp WHERE updated_at IS NULL')
    
    # Add updated_at to ocr_results table
    op.add_column('ocr_results', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')))


def downgrade() -> None:
    # Remove columns
    op.drop_column('ocr_results', 'updated_at')
    op.drop_column('documents', 'updated_at')
    op.drop_column('documents', 'created_at')
