"""add official_url to gyms

Revision ID: f4d2c1b3a789
Revises: b3a9d1352d6c
Create Date: 2025-09-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4d2c1b3a789"
down_revision: str | None = "b3a9d1352d6c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    column_names = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in column_names


def upgrade() -> None:
    if not _column_exists("gyms", "official_url"):
        op.add_column("gyms", sa.Column("official_url", sa.Text(), nullable=True))


def downgrade() -> None:
    if _column_exists("gyms", "official_url"):
        op.drop_column("gyms", "official_url")
