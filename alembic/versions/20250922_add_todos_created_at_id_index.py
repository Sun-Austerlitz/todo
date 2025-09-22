"""add composite index on todos (created_at desc, id desc)

Revision ID: 20250922_add_todos_created_at_id_index
Revises: 
Create Date: 2025-09-22 00:00:00.000001
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'todos_idx_createdat_id_20250922'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_todos_created_at_id', 'todos', ['created_at', 'id'], postgresql_using='btree')


def downgrade():
    op.drop_index('ix_todos_created_at_id', table_name='todos')
