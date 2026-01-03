"""merge gym_id and fields migrations

Revision ID: i7g5h4f3e2d1
Revises: 2a32b6dbce3e, h6f4g3e2d1c0
Create Date: 2026-01-03 17:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "i7g5h4f3e2d1"
down_revision: tuple[str, str] = ("2a32b6dbce3e", "h6f4g3e2d1c0")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # No-op merge migration
    pass


def downgrade() -> None:
    # No-op merge migration
    pass
