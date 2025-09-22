"""add fk on replaced_by_id, index on expires_at, and device_type check

Revision ID: ea1b3c4d5f67
Revises: df3a1b2e9add
Create Date: 2025-09-21 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'ea1b3c4d5f67'
down_revision = 'df3a1b2e9add'
branch_labels = None
depends_on = None


def upgrade():
    # Create index on expires_at for faster queries and retention jobs
    op.create_index('ix_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'])

    # Add FK constraint for replaced_by_id referencing same table
    # Use ON DELETE SET NULL to avoid cascading deletes of replacement history
    op.create_foreign_key(
        'fk_refresh_replaced_by',
        'refresh_tokens', 'refresh_tokens',
        ['replaced_by_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add CHECK constraint to enforce device_type values at DB level (Postgres)
    op.execute("""
    ALTER TABLE refresh_tokens
    ADD CONSTRAINT ck_refresh_device_type
    CHECK (device_type IN ('web','mobile') OR device_type IS NULL);
    """)


def downgrade():
    op.execute('ALTER TABLE refresh_tokens DROP CONSTRAINT IF EXISTS ck_refresh_device_type;')
    op.drop_constraint('fk_refresh_replaced_by', 'refresh_tokens', type_='foreignkey')
    op.drop_index('ix_refresh_tokens_expires_at', table_name='refresh_tokens')
