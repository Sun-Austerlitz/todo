"""add device_type to refresh_tokens

Revision ID: df3a1b2e9add
Revises: ae7f1b2c9d4f
Create Date: 2025-09-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'df3a1b2e9add'
down_revision = 'cd3f7b8a9f1c'
branch_labels = None
depends_on = None


def upgrade():
    # Add nullable device_type column
    op.add_column('refresh_tokens', sa.Column('device_type', sa.String(length=100), nullable=True))
    # Create index for device_type
    op.create_index('ix_refresh_tokens_device_type', 'refresh_tokens', ['device_type'], unique=False)
    # Create a partial unique index to ensure at most one active (not revoked) token per user+device_type
    # Note: partial indexes are Postgres specific; if running other DBs this step will need to be adapted.
    op.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS ux_refresh_user_device_active
    ON refresh_tokens (user_id, device_type)
    WHERE (revoked = false AND device_type IS NOT NULL);
    """)


def downgrade():
    op.execute('DROP INDEX IF EXISTS ux_refresh_user_device_active;')
    op.drop_index('ix_refresh_tokens_device_type', table_name='refresh_tokens')
    op.drop_column('refresh_tokens', 'device_type')
