"""add reports table

Revision ID: f1a2b3c4d5e6
Revises: cc12d3f8a7b1
Create Date: 2025-09-12 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "cc12d3f8a7b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "gym_id", sa.Integer(), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_reports_gym_id", "reports", ["gym_id"])
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_created_at", "reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_reports_created_at", table_name="reports")
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_index("ix_reports_gym_id", table_name="reports")
    op.drop_table("reports")
