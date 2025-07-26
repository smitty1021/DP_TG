-- Create a new migration file: migrations/versions/remove_profile_picture_column.py

"""Remove profile_picture column from user table

Revision ID: remove_profile_picture
Revises: 1d6806c3799b
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'remove_profile_picture'
down_revision = '1d6806c3799b'  # Replace with your latest migration ID
branch_labels = None
depends_on = None

def upgrade():
    # Remove the profile_picture column from the user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('profile_picture')

def downgrade():
    # Add the profile_picture column back if needed to rollback
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_picture', sa.String(length=200), nullable=True))