"""add latitude/longitude columns to gyms

Revision ID: cc12d3f8a7b1
Revises: a210e2f5d9ab
Create Date: 2025-09-12 22:30:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Alembic identifiers
revision: str = "cc12d3f8a7b1"
down_revision: str | Sequence[str] | None = "a210e2f5d9ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("gyms", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("gyms", sa.Column("longitude", sa.Float(), nullable=True))
    op.create_index("ix_gyms_latitude", "gyms", ["latitude"], unique=False)
    op.create_index("ix_gyms_longitude", "gyms", ["longitude"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_gyms_longitude", table_name="gyms")
    op.drop_index("ix_gyms_latitude", table_name="gyms")
    op.drop_column("gyms", "longitude")
    op.drop_column("gyms", "latitude")
