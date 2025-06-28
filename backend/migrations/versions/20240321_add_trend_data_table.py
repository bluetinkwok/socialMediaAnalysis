"""Add trend data table

Revision ID: 20240321_add_trend_data
Revises: 20240320_add_analytics_data
Create Date: 2024-03-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240321_add_trend_data'
down_revision = '20240320_add_analytics_data'
branch_labels = None
depends_on = None


def upgrade():
    # Create trend_data table
    op.create_table(
        'trend_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trend_type', sa.String(length=50), nullable=False),
        sa.Column('trend_value', sa.String(length=255), nullable=False),
        sa.Column('platform', sa.Enum('YOUTUBE', 'INSTAGRAM', 'THREADS', 'REDNOTE', name='platformtype'), nullable=False),
        sa.Column('occurrence_count', sa.Integer(), nullable=True, default=1),
        sa.Column('engagement_sum', sa.Integer(), nullable=True, default=0),
        sa.Column('trend_score', sa.Float(), nullable=True),
        sa.Column('trend_date', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_trend_data_id'), 'trend_data', ['id'], unique=False)
    op.create_index(op.f('ix_trend_data_trend_type'), 'trend_data', ['trend_type'], unique=False)
    op.create_index(op.f('ix_trend_data_platform'), 'trend_data', ['platform'], unique=False)
    op.create_index(op.f('ix_trend_data_trend_date'), 'trend_data', ['trend_date'], unique=False)
    op.create_index(op.f('ix_trend_data_window_start'), 'trend_data', ['window_start'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_trend_data_window_start'), table_name='trend_data')
    op.drop_index(op.f('ix_trend_data_trend_date'), table_name='trend_data')
    op.drop_index(op.f('ix_trend_data_platform'), table_name='trend_data')
    op.drop_index(op.f('ix_trend_data_trend_type'), table_name='trend_data')
    op.drop_index(op.f('ix_trend_data_id'), table_name='trend_data')
    
    # Drop trend_data table
    op.drop_table('trend_data') 