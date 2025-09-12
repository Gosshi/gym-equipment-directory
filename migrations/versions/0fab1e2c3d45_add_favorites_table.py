"""add favorites table

Revision ID: 0fab1e2c3d45
Revises: f1a2b3c4d5e6
Create Date: 2025-09-12 00:00:01.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0fab1e2c3d45"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "favorites",
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column(
            "gym_id", sa.Integer(), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("device_id", "gym_id"),
    )
    # Composite PK (device_id, gym_id) can serve listing by device_id efficiently.


def downgrade() -> None:
    op.drop_table("favorites")
