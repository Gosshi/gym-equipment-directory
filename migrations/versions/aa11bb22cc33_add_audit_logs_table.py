"""add audit_logs table

Revision ID: aa11bb22cc33
Revises: c7cf8e913d2a
Create Date: 2025-11-20 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa11bb22cc33"
down_revision: str | None = "c7cf8e913d2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("operator", sa.String(length=128), nullable=True),
        sa.Column("candidate_ids", sa.JSON(), nullable=False),
        sa.Column("success_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("failure_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("request_meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")
