"""add canonical_id to gyms"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.services.canonical import make_canonical_id

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "5d74d73e056c"
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
        sa.column("pref", sa.String),
        sa.column("city", sa.String),
        sa.column("canonical_id", postgresql.UUID(as_uuid=False)),
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.select(gyms_table.c.id, gyms_table.c.name, gyms_table.c.pref, gyms_table.c.city)
    ).all()
    for row in rows:
        canonical = make_canonical_id(row.pref, row.city, row.name or "")
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
