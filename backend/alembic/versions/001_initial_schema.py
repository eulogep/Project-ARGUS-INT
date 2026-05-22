"""initial schema

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-05-22 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Enable UUID Extension if not present
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # 2. Create investigations table
    op.create_table(
        'investigations',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('target', sa.Text(), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('depth', sa.Integer(), server_default='1', nullable=True),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=True),
        sa.Column('result_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('pivot_suggestions', sa.Text(), nullable=True),
        sa.Column('llm_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMPTZ(), server_default=sa.func.now(), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMPTZ(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'COLLECTING', 'CORRELATING', 'COMPLETED', 'DONE', 'FAILED')",
            name='status_check'
        )
    )
    op.create_index('idx_investigations_status', 'investigations', ['status'])
    op.create_index('idx_investigations_created_at', 'investigations', [sa.text('created_at DESC')])

    # 3. Create raw_results table
    op.create_table(
        'raw_results',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('investigation_id', sa.UUID(), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('module', sa.String(length=100), nullable=False),
        sa.Column('source', sa.String(length=200), nullable=True),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), server_default='0.5', nullable=True),
        sa.Column('sha256_hash', sa.CHAR(length=64), nullable=True),
        sa.Column('created_at', sa.TIMESTAMPTZ(), server_default=sa.func.now(), nullable=True)
    )

    # 4. Create archives table
    op.create_table(
        'archives',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('investigation_id', sa.UUID(), sa.ForeignKey('investigations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('archive_url', sa.Text(), nullable=True),
        sa.Column('sha256_hash', sa.CHAR(length=64), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('captured_at', sa.TIMESTAMPTZ(), server_default=sa.func.now(), nullable=True),
        sa.Column('diff_from_previous', sa.Text(), nullable=True)
    )

    # 5. Create reports table
    op.create_table(
        'reports',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('investigation_id', sa.UUID(), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('format', sa.String(length=20), server_default='JSON', nullable=True),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('sha256_hash', sa.CHAR(length=64), nullable=True),
        sa.Column('generated_at', sa.TIMESTAMPTZ(), server_default=sa.func.now(), nullable=True)
    )

def downgrade() -> None:
    op.drop_table('reports')
    op.drop_table('archives')
    op.drop_table('raw_results')
    op.drop_table('investigations')
