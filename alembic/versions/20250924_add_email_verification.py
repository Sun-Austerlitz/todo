"""add email verification columns to users

Revision ID: add_email_verification_20250924
Revises: merge_20250923
Create Date: 2025-09-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_email_verification_20250924'
down_revision = 'merge_20250923'
branch_labels = None
depends_on = None


def upgrade():
    # Add verification token and expiry columns
    op.add_column('users', sa.Column('verification_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('verification_expires', sa.DateTime(timezone=True), nullable=True))

    # Make new user accounts default to inactive at the DB level as well
    op.alter_column('users', 'is_active', server_default=sa.text('false'))


def downgrade():
    # Revert is_active default
    op.alter_column('users', 'is_active', server_default=None)
    # Drop verification columns
    op.drop_column('users', 'verification_expires')
    op.drop_column('users', 'verification_token')
