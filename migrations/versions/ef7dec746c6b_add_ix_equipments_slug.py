"""add ix_equipments_slug

Revision ID: ef7dec746c6b
Revises: e86e78f43ec1
Create Date: 2025-09-06 01:00:39.536387

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ef7dec746c6b"
down_revision: str | None = "e86e78f43ec1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    # CONCURRENTLY はトランザクション外が必須
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_equipments_slug ON equipments (slug)"
        )


def downgrade():
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_equipments_slug")
