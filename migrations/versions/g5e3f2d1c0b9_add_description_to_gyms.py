"""add description to gyms

Revision ID: g5e3f2d1c0b9
Revises: f4d2c1b3a789
Create Date: 2026-01-02 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g5e3f2d1c0b9"
down_revision: str | None = "f4d2c1b3a789"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    column_names = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in column_names


def upgrade() -> None:
    if not _column_exists("gyms", "description"):
        op.add_column("gyms", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    if _column_exists("gyms", "description"):
        op.drop_column("gyms", "description")
