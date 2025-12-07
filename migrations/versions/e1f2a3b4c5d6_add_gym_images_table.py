"""add gym_images table

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2025-09-13 09:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gym_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "gym_id", sa.Integer(), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_gym_images_gym_id", "gym_images", ["gym_id"])
    op.create_index("ix_gym_images_created_at", "gym_images", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_gym_images_created_at", table_name="gym_images")
    op.drop_index("ix_gym_images_gym_id", table_name="gym_images")
    op.drop_table("gym_images")
