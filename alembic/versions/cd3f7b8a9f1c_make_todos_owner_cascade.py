"""make todos.owner_id cascade on delete

Revision ID: cd3f7b8a9f1c
Revises: ba9d4f1e8c2b
Create Date: 2025-09-19 00:50:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'cd3f7b8a9f1c'
down_revision = 'ba9d4f1e8c2b'
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing constraint if present, then add new one with CASCADE
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'todos'
                AND tc.constraint_name = 'fk_todos_owner_id_users'
            ) THEN
                ALTER TABLE todos DROP CONSTRAINT fk_todos_owner_id_users;
            END IF;
            ALTER TABLE todos
            ADD CONSTRAINT fk_todos_owner_id_users
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE;
        END$$;
        """
    )


def downgrade():
    # Revert back to RESTRICT
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'todos'
                AND tc.constraint_name = 'fk_todos_owner_id_users'
            ) THEN
                ALTER TABLE todos DROP CONSTRAINT fk_todos_owner_id_users;
            END IF;
            ALTER TABLE todos
            ADD CONSTRAINT fk_todos_owner_id_users
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE RESTRICT;
        END$$;
        """
    )
