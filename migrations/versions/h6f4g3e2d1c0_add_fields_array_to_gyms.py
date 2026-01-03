"""add fields array to gyms

Revision ID: h6f4g3e2d1c0
Revises: g5e3f2d1c0b9
Create Date: 2026-01-03 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "h6f4g3e2d1c0"
down_revision: str | None = "g5e3f2d1c0b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    column_names = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in column_names


def upgrade() -> None:
    # Add fields JSONB array column
    if not _column_exists("gyms", "fields"):
        op.add_column("gyms", sa.Column("fields", JSONB, nullable=True))


def downgrade() -> None:
    if _column_exists("gyms", "fields"):
        op.drop_column("gyms", "fields")
