"""add_category_column

Revision ID: ac7dcd2ec590
Revises: a29ad1005ede
Create Date: 2025-12-26 14:26:29.137966

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ac7dcd2ec590"
down_revision: str | None = "a29ad1005ede"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add category column to gym_candidates
    op.add_column("gym_candidates", sa.Column("category", sa.String(length=32), nullable=True))
    # Add category column to gyms
    op.add_column("gyms", sa.Column("category", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("gyms", "category")
    op.drop_column("gym_candidates", "category")
