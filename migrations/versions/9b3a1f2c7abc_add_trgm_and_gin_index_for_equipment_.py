"""add pg_trgm and GIN index for equipments.name

Revision ID: 9b3a1f2c7abc
Revises: 5d74d73e056c
Create Date: 2025-09-12 19:30:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b3a1f2c7abc"
down_revision: str | None = "5d74d73e056c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    # Ensure pg_trgm extension exists (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # Trigram GIN index for ILIKE/LIKE on equipments.name
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_equipments_name_trgm "
        "ON equipments USING gin (name gin_trgm_ops)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_equipments_name_trgm")
