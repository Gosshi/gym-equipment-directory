"""add ix_equipments_slug

Revision ID: ef7dec746c6b
Revises: e86e78f43ec1
Create Date: 2025-09-06 01:00:39.536387

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ef7dec746c6b"
down_revision: Union[str, None] = "e86e78f43ec1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # CONCURRENTLY はトランザクション外が必須
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_equipments_slug ON equipments (slug)"
        )


def downgrade():
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_equipments_slug")
