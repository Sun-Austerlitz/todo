"""create refresh_tokens table

Revision ID: ae7f1b2c9d4f
Revises: c562493547f9
Create Date: 2025-09-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ae7f1b2c9d4f'
down_revision = 'c562493547f9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer, nullable=False, index=True),
        sa.Column('token_hash', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('device_id', sa.String(length=255), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('ip_address', sa.String(length=100), nullable=True),
        sa.Column('replaced_by_id', sa.Integer, nullable=True),
    )
    # Create indexes if they do not already exist (safe for partially-applied DBs)
    op.execute("CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON refresh_tokens (token_hash);")


def downgrade():
    # Downgrade: drop indexes if exist and drop table
    op.execute("DROP INDEX IF EXISTS ix_refresh_tokens_token_hash;")
    op.execute("DROP INDEX IF EXISTS ix_refresh_tokens_user_id;")
    op.drop_table('refresh_tokens')
