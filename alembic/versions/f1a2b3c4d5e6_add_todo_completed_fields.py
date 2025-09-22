"""add completed_at and completed_by to todos

Revision ID: f1a2b3c4d5e6
Revises: ea1b3c4d5f67
Create Date: 2025-09-21 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'ea1b3c4d5f67'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('todos', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('todos', sa.Column('completed_by', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_todos_completed_by_users', 'todos', 'users', ['completed_by'], ['id'], ondelete='SET NULL')


def downgrade():
    op.drop_constraint('fk_todos_completed_by_users', 'todos', type_='foreignkey')
    op.drop_column('todos', 'completed_by')
    op.drop_column('todos', 'completed_at')
