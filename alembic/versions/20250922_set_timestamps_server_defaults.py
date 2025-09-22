"""set timestamps to server defaults and add updated_at trigger

Revision ID: 20250922_set_timestamps_server_defaults
Revises: 
Create Date: 2025-09-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ts_defaults_20250922'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    # Set server default for created_at and updated_at to now()
    op.alter_column('users', 'created_at', server_default=sa.text('now()'))
    op.alter_column('users', 'updated_at', server_default=sa.text('now()'))
    op.alter_column('todos', 'created_at', server_default=sa.text('now()'))
    op.alter_column('todos', 'updated_at', server_default=sa.text('now()'))
    op.alter_column('refresh_tokens', 'issued_at', server_default=sa.text('now()'))

    # Create trigger function for updated_at
    op.execute("""
    CREATE OR REPLACE FUNCTION touch_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = now();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # Attach trigger to tables that need updated_at auto-update
    op.execute("""
    CREATE TRIGGER touch_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();
    """)

    op.execute("""
    CREATE TRIGGER touch_todos_updated_at
    BEFORE UPDATE ON todos
    FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();
    """)


def downgrade():
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS touch_todos_updated_at ON todos;')
    op.execute('DROP TRIGGER IF EXISTS touch_users_updated_at ON users;')
    # Drop trigger function
    op.execute('DROP FUNCTION IF EXISTS touch_updated_at();')

    # Remove server defaults
    op.alter_column('users', 'created_at', server_default=None)
    op.alter_column('users', 'updated_at', server_default=None)
    op.alter_column('todos', 'created_at', server_default=None)
    op.alter_column('todos', 'updated_at', server_default=None)
    op.alter_column('refresh_tokens', 'issued_at', server_default=None)
