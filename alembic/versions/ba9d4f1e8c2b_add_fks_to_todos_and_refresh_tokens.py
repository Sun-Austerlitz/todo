"""add foreign keys to todos and refresh_tokens

Revision ID: ba9d4f1e8c2b
Revises: ae7f1b2c9d4f
Create Date: 2025-09-19 00:30:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'ba9d4f1e8c2b'
down_revision = 'ae7f1b2c9d4f'
branch_labels = None
depends_on = None


def upgrade():
    # Add foreign key on todos.owner_id -> users.id (RESTRICT on delete)
    # Safety: only add constraint if it does not already exist
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'todos'
                AND tc.constraint_name = 'fk_todos_owner_id_users'
            ) THEN
                ALTER TABLE todos
                ADD CONSTRAINT fk_todos_owner_id_users
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE RESTRICT;
            END IF;
        END$$;
        """
    )

    # Add foreign key on refresh_tokens.user_id -> users.id (CASCADE on delete)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'refresh_tokens'
                AND tc.constraint_name = 'fk_refresh_tokens_user_id_users'
            ) THEN
                ALTER TABLE refresh_tokens
                ADD CONSTRAINT fk_refresh_tokens_user_id_users
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
            END IF;
        END$$;
        """
    )


def downgrade():
    # Drop constraints if exist
    op.execute("ALTER TABLE IF EXISTS refresh_tokens DROP CONSTRAINT IF EXISTS fk_refresh_tokens_user_id_users;")
    op.execute("ALTER TABLE IF EXISTS todos DROP CONSTRAINT IF EXISTS fk_todos_owner_id_users;")
