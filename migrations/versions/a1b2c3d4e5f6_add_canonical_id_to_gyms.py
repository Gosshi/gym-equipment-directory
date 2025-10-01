"""add canonical_id to gyms"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.services.canonical import NAMESPACE_GYM, normalize_name

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "c5f2d68f2b31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "gyms",
        sa.Column("canonical_id", postgresql.UUID(as_uuid=False), nullable=True),
    )

    gyms_table = sa.table(
        "gyms",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("pref", sa.String),
        sa.column("city", sa.String),
        sa.column("canonical_id", postgresql.UUID(as_uuid=False)),
    )

    def _canonical_key(pref: str | None, city: str | None, name: str | None) -> str:
        pref_part = (pref or "").strip().lower()
        city_part = (city or "").strip().lower()
        name_part = normalize_name(name or "").lower()
        return "|".join([pref_part, city_part, name_part])

    conn = op.get_bind()
    rows = conn.execute(
        sa.select(
            gyms_table.c.id,
            gyms_table.c.name,
            gyms_table.c.slug,
            gyms_table.c.pref,
            gyms_table.c.city,
        ).order_by(gyms_table.c.id)
    ).all()

    assigned: dict[str, int] = {}
    for row in rows:
        key = _canonical_key(row.pref, row.city, row.name)
        canonical = str(uuid.uuid5(NAMESPACE_GYM, key))
        if canonical in assigned:
            slug_part = (row.slug or "").strip().lower()
            fallback_key = f"{key}|slug:{slug_part}|row:{row.id}"
            canonical = str(uuid.uuid5(NAMESPACE_GYM, fallback_key))
            while canonical in assigned:
                fallback_key = f"{fallback_key}|dedupe"
                canonical = str(uuid.uuid5(NAMESPACE_GYM, fallback_key))
        assigned[canonical] = row.id
        conn.execute(
            gyms_table.update().where(gyms_table.c.id == row.id).values(canonical_id=canonical)
        )

    op.alter_column(
        "gyms",
        "canonical_id",
        existing_type=postgresql.UUID(as_uuid=False),
        nullable=False,
    )
    op.create_index(
        "uq_gyms_canonical_id",
        "gyms",
        ["canonical_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_gyms_canonical_id", table_name="gyms")
    op.drop_column("gyms", "canonical_id")
