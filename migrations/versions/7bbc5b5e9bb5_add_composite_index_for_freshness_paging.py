"""add composite index for freshness paging

Revision ID: 7bbc5b5e9bb5
Revises: e9b46ddd3871
Create Date: 2025-09-05 22:05:08.546634

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7bbc5b5e9bb5'
down_revision: Union[str, None] = 'e9b46ddd3871'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_gyms_freshness_paging
            ON gyms (last_verified_at_cached DESC, id ASC)
            WHERE last_verified_at_cached IS NOT NULL
        """)

def downgrade():
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_gyms_freshness_paging")
