"""add_categories_to_candidates

Revision ID: 569d787b4ad5
Revises: add_categories_array
Create Date: 2026-01-01 05:36:55.884418

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "569d787b4ad5"
down_revision: str | None = "add_categories_array"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "gym_candidates", sa.Column("categories", postgresql.ARRAY(sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("gym_candidates", "categories")
