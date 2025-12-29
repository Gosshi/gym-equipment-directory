"""Add categories array column

Revision ID: add_categories_array
Revises: ac7dcd2ec590
Create Date: 2025-12-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_categories_array"
down_revision: str | None = "ac7dcd2ec590"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add new categories column as TEXT[]
    op.add_column(
        "gyms",
        sa.Column("categories", postgresql.ARRAY(sa.Text()), nullable=True),
    )

    # Migrate existing category data to categories array
    # Convert single category to array: 'gym' -> ['gym']
    op.execute(
        """
        UPDATE gyms 
        SET categories = ARRAY[category]::text[]
        WHERE category IS NOT NULL AND categories IS NULL
        """
    )

    # Set default for null categories
    op.execute(
        """
        UPDATE gyms 
        SET categories = ARRAY['gym']::text[]
        WHERE categories IS NULL
        """
    )


def downgrade() -> None:
    # Drop categories column
    op.drop_column("gyms", "categories")
