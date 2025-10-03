"""add official_url to gyms

Revision ID: f4d2c1b3a789
Revises: e9b46ddd3871
Create Date: 2025-09-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4d2c1b3a789"
down_revision: str | None = "e9b46ddd3871"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("gyms")}
    if "official_url" not in columns:
        op.add_column("gyms", sa.Column("official_url", sa.Text(), nullable=True))
    else:
        op.alter_column(
            "gyms",
            "official_url",
            existing_type=sa.String(),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("gyms")}
    if "official_url" in columns:
        op.drop_column("gyms", "official_url")
