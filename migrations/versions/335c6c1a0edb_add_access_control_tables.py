"""add_access_control_tables

Revision ID: 335c6c1a0edb
Revises: ad6e938c053d
Create Date: 2025-07-26 09:58:58.974531

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '335c6c1a0edb'
down_revision = 'ad6e938c053d'
branch_labels = None
depends_on = None


def upgrade():
    # Create page_access_permissions table
    op.create_table('page_access_permissions',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('discord_role_id', sa.String(length=255), nullable=False),
                    sa.Column('page_endpoint', sa.String(length=255), nullable=False),
                    sa.Column('page_name', sa.String(length=255), nullable=False),
                    sa.Column('page_category', sa.String(length=100), nullable=True),
                    sa.Column('is_allowed', sa.Boolean(), nullable=False, default=True),
                    sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.current_timestamp()),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('created_by', sa.String(length=100), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('discord_role_id', 'page_endpoint', name='uq_role_page')
                    )

    # Create indexes for page_access_permissions
    op.create_index('ix_page_access_role_id', 'page_access_permissions', ['discord_role_id'])
    op.create_index('ix_page_access_endpoint', 'page_access_permissions', ['page_endpoint'])

    # Create access_control_groups table
    op.create_table('access_control_groups',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('group_key', sa.String(length=100), nullable=False),
                    sa.Column('group_name', sa.String(length=255), nullable=False),
                    sa.Column('description', sa.Text(), nullable=True),
                    sa.Column('pages', sa.JSON(), nullable=False),
                    sa.Column('is_system_group', sa.Boolean(), nullable=False, default=False),
                    sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
                    sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.current_timestamp()),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('created_by', sa.String(length=100), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('group_key')
                    )

    # Create user_access_logs table
    op.create_table('user_access_logs',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=True),
                    sa.Column('discord_id', sa.String(length=255), nullable=True),
                    sa.Column('attempted_page', sa.String(length=255), nullable=False),
                    sa.Column('access_granted', sa.Boolean(), nullable=False),
                    sa.Column('reason_denied', sa.String(length=255), nullable=True),
                    sa.Column('user_roles', sa.JSON(), nullable=True),
                    sa.Column('access_level', sa.String(length=50), nullable=True),
                    sa.Column('ip_address', sa.String(length=45), nullable=True),
                    sa.Column('user_agent', sa.Text(), nullable=True),
                    sa.Column('timestamp', sa.DateTime(), nullable=False, default=sa.func.current_timestamp()),
                    sa.ForeignKeyConstraint(['user_id'], ['user.id']),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Create indexes for user_access_logs
    op.create_index('ix_access_logs_user_id', 'user_access_logs', ['user_id'])
    op.create_index('ix_access_logs_timestamp', 'user_access_logs', ['timestamp'])

    # Create role_permission_templates table
    op.create_table('role_permission_templates',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('template_name', sa.String(length=255), nullable=False),
                    sa.Column('description', sa.Text(), nullable=True),
                    sa.Column('permission_config', sa.JSON(), nullable=False),
                    sa.Column('is_system_template', sa.Boolean(), nullable=False, default=False),
                    sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
                    sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.current_timestamp()),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('created_by', sa.String(length=100), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('template_name')
                    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table('role_permission_templates')
    op.drop_table('user_access_logs')
    op.drop_table('access_control_groups')
    op.drop_table('page_access_permissions')