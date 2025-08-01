"""Add CASCADE DELETE to P12UsageStats foreign key

Revision ID: ca6aa4899f81
Revises: 335c6c1a0edb
Create Date: 2025-07-31 11:16:48.088698

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ca6aa4899f81'
down_revision = '335c6c1a0edb'
branch_labels = None
depends_on = None


def upgrade():
    # For SQLite, we need to recreate the table to change foreign key constraints
    # First, create a new table with the correct foreign key constraint
    op.create_table('p12_usage_stats_new',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('p12_scenario_id', sa.Integer(), nullable=False),
        sa.Column('journal_date', sa.Date(), nullable=False),
        sa.Column('selection_timestamp', sa.DateTime(), nullable=False),
        sa.Column('market_session', sa.String(length=50), nullable=True),
        sa.Column('p12_high', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('p12_mid', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('p12_low', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('outcome_successful', sa.Boolean(), nullable=True),
        sa.Column('outcome_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['p12_scenario_id'], ['p12_scenario.id'], ondelete='CASCADE'),
    )
    
    # Copy data from old table to new table
    op.execute('INSERT INTO p12_usage_stats_new SELECT * FROM p12_usage_stats')
    
    # Drop old table and rename new table
    op.drop_table('p12_usage_stats')
    op.rename_table('p12_usage_stats_new', 'p12_usage_stats')


def downgrade():
    # Recreate without CASCADE
    op.create_table('p12_usage_stats_new',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('p12_scenario_id', sa.Integer(), nullable=False),
        sa.Column('journal_date', sa.Date(), nullable=False),
        sa.Column('selection_timestamp', sa.DateTime(), nullable=False),
        sa.Column('market_session', sa.String(length=50), nullable=True),
        sa.Column('p12_high', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('p12_mid', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('p12_low', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('outcome_successful', sa.Boolean(), nullable=True),
        sa.Column('outcome_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['p12_scenario_id'], ['p12_scenario.id'], ),
    )
    
    # Copy data from old table to new table
    op.execute('INSERT INTO p12_usage_stats_new SELECT * FROM p12_usage_stats')
    
    # Drop old table and rename new table
    op.drop_table('p12_usage_stats')
    op.rename_table('p12_usage_stats_new', 'p12_usage_stats')
