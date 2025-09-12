"""add pg_trgm and GIN(trgm) indexes for gyms.name and gyms.city

Revision ID: d4e5f6a7b8c9
Revises: 0fab1e2c3d45
Create Date: 2025-09-13 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "0fab1e2c3d45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    # Ensure pg_trgm extension exists (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # Trigram GIN indexes for partial match performance on gyms
    op.execute("CREATE INDEX IF NOT EXISTS ix_gyms_name_trgm ON gyms USING gin (name gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gyms_city_trgm ON gyms USING gin (city gin_trgm_ops)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_gyms_city_trgm")
    op.execute("DROP INDEX IF EXISTS ix_gyms_name_trgm")
