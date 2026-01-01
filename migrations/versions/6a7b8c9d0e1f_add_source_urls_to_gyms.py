"""add source_urls to gyms

Revision ID: 6a7b8c9d0e1f
Revises: 569d787b4ad5
Create Date: 2026-01-01 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

# revision identifiers, used by Alembic.
revision: str = "6a7b8c9d0e1f"
down_revision: str | None = "569d787b4ad5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    column_names = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in column_names


def upgrade() -> None:
    if not _column_exists("gyms", "source_urls"):
        op.add_column("gyms", sa.Column("source_urls", ARRAY(sa.Text()), nullable=True))


def downgrade() -> None:
    if _column_exists("gyms", "source_urls"):
        op.drop_column("gyms", "source_urls")
