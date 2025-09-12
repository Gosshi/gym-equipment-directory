"""merge heads after trgm and indexrs

Revision ID: a210e2f5d9ab
Revises: bb2498dc0236, 9b3a1f2c7abc
Create Date: 2025-09-12 20:05:00.000000

"""

from collections.abc import Sequence

# Alembic identifiers
revision: str = "a210e2f5d9ab"
down_revision: tuple[str, str] | None = ("bb2498dc0236", "9b3a1f2c7abc")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    # Merge point; no-op
    pass


def downgrade():
    # Un-merge; no-op
    pass
