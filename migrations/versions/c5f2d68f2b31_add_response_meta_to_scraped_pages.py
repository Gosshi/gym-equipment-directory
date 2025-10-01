"""add response_meta to scraped_pages

Revision ID: c5f2d68f2b31
Revises: 1a3f2c4b5d67
Create Date: 2025-10-01 10:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5f2d68f2b31"
down_revision: str | None = "1a3f2c4b5d67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE scraped_pages ADD COLUMN IF NOT EXISTS response_meta JSONB",
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE scraped_pages DROP COLUMN IF EXISTS response_meta",
    )
