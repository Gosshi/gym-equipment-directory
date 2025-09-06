"""add indexes for gyms/equipments

Revision ID: 12343e69c3de
Revises: ef7dec746c6b
Create Date: 2025-09-06 01:22:57.774495

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12343e69c3de'
down_revision: Union[str, None] = 'ef7dec746c6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # equipments.slug 用 BTREE（LIKE/等価クエリ想定）
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_equipments_slug "
            "ON equipments (slug)"
        )

    # gyms の部分・複合インデックス（DESC/ASC + WHERE IS NOT NULL）
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_gyms_lvac_desc_id_asc_notnull "
            "ON gyms (last_verified_at_cached DESC, id ASC) "
            "WHERE last_verified_at_cached IS NOT NULL"
        )

def downgrade():
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX IF EXISTS ix_gyms_lvac_desc_id_asc_notnull")
        op.execute("DROP INDEX IF EXISTS ix_equipments_slug")