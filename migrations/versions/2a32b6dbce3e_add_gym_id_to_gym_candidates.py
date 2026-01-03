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


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    column_names = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in column_names


def upgrade() -> None:
    # Add gym_id column with foreign key to gyms table (if not exists)
    if not _column_exists("gym_candidates", "gym_id"):
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
    if _column_exists("gym_candidates", "gym_id"):
        op.drop_index("ix_gym_candidates_gym_id", table_name="gym_candidates")
        op.drop_constraint("fk_gym_candidates_gym_id", "gym_candidates", type_="foreignkey")
        op.drop_column("gym_candidates", "gym_id")
