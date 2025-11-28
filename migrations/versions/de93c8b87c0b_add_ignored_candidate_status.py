"""Add ignored to candidate_status enum

Revision ID: de93c8b87c0b
Revises: aa11bb22cc33
Create Date: 2025-11-27 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "de93c8b87c0b"
down_revision: str | None = "aa11bb22cc33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE candidate_status ADD VALUE IF NOT EXISTS 'ignored'")


def downgrade() -> None:
    op.execute(
        "CREATE TYPE candidate_status_old AS ENUM "
        "('new', 'reviewing', 'approved', 'rejected')"
    )
    op.execute("ALTER TABLE gym_candidates ALTER COLUMN status DROP DEFAULT")
    op.execute("UPDATE gym_candidates SET status = 'rejected' WHERE status = 'ignored'")
    op.execute(
        "ALTER TABLE gym_candidates ALTER COLUMN status TYPE candidate_status_old "
        "USING status::text::candidate_status_old"
    )
    op.execute("DROP TYPE candidate_status")
    op.execute("ALTER TYPE candidate_status_old RENAME TO candidate_status")
    op.execute("ALTER TABLE gym_candidates ALTER COLUMN status SET DEFAULT 'new'::candidate_status")
