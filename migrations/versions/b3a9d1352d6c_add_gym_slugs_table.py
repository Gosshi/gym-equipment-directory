"""add gym_slugs table and backfill current slugs

Revision ID: b3a9d1352d6c
Revises: a210e2f5d9ab
Create Date: 2024-10-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3a9d1352d6c"
down_revision: str | Sequence[str] | None = "a210e2f5d9ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gym_slugs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "gym_id", sa.BigInteger(), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_gym_slugs_gym_id", "gym_slugs", ["gym_id"], unique=False)

    connection = op.get_bind()
    gyms = connection.execute(
        sa.text("SELECT id, slug FROM gyms WHERE slug IS NOT NULL")
    ).fetchall()
    if gyms:
        gym_slugs_table = sa.table(
            "gym_slugs",
            sa.Column("gym_id", sa.BigInteger()),
            sa.Column("slug", sa.Text()),
            sa.Column("is_current", sa.Boolean()),
        )
        op.bulk_insert(
            gym_slugs_table,
            [
                {"gym_id": int(row.id), "slug": row.slug, "is_current": True}
                for row in gyms
                if row.slug
            ],
        )


def downgrade() -> None:
    op.drop_index("ix_gym_slugs_gym_id", table_name="gym_slugs")
    op.drop_table("gym_slugs")
