# Merge heads for the two new revisions
"""
Revision ID: merge_20250923
Revises: todos_idx_createdat_id_20250922, ts_defaults_20250922
Create Date: 2025-09-23 00:00:00.000000
"""
# merge-only revision; no operations required

# revision identifiers, used by Alembic.
revision = 'merge_20250923'
down_revision = (
    'todos_idx_createdat_id_20250922',
    'ts_defaults_20250922',
)
branch_labels = None
depends_on = None


def upgrade():
    # Merge-only revision: no DB operations; serves to join branches
    pass


def downgrade():
    # Downgrade would re-split heads; leave as no-op to avoid complex history rewrites
    pass
