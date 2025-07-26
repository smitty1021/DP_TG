"""Remove profile_picture column from user table

Revision ID: ad6e938c053d
Revises: 1d6806c3799b
Create Date: 2025-07-25 15:16:53.387173

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ad6e938c053d'
down_revision = '1d6806c3799b'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
