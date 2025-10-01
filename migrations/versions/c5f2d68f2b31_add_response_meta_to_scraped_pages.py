"""add response_meta to scraped_pages

Revision ID: c5f2d68f2b31
Revises: 1a3f2c4b5d67
Create Date: 2025-10-01 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c5f2d68f2b31"
down_revision: str | None = "1a3f2c4b5d67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scraped_pages",
        sa.Column("response_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scraped_pages", "response_meta")
