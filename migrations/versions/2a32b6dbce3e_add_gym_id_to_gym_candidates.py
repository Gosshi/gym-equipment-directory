"""add gym_id to gym_candidates

Revision ID: 2a32b6dbce3e
Revises: g5e3f2d1c0b9
Create Date: 2026-01-03 16:04:54.414167

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a32b6dbce3e"
down_revision: str | None = "g5e3f2d1c0b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add gym_id column with foreign key to gyms table
    op.add_column("gym_candidates", sa.Column("gym_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_gym_candidates_gym_id",
        "gym_candidates",
        "gyms",
        ["gym_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_gym_candidates_gym_id", "gym_candidates", ["gym_id"])


def downgrade() -> None:
    op.drop_index("ix_gym_candidates_gym_id", table_name="gym_candidates")
    op.drop_constraint("fk_gym_candidates_gym_id", "gym_candidates", type_="foreignkey")
    op.drop_column("gym_candidates", "gym_id")
