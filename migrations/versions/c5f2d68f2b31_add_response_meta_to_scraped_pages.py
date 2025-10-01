"""add response_meta column to scraped_pages

Revision ID: c5f2d68f2b31
Revises: 1a3f2c4b5d67
Create Date: 2024-05-24 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = "c5f2d68f2b31"
down_revision = "1a3f2c4b5d67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scraped_pages",
        sa.Column("response_meta", pg.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scraped_pages", "response_meta")
