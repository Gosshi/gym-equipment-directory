"""add composite index for gyms search

Revision ID: 3b6b1231bf9a
Revises: 12343e69c3de
Create Date: 2025-09-06 01:31:38.143043

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3b6b1231bf9a"
down_revision: str | None = "12343e69c3de"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    # gyms(pref, city, last_verified_at_cached DESC, id ASC)
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_gyms_pref_city_lvac_desc_id_asc "
            "ON gyms (prefecture, city, last_verified_at_cached DESC, id ASC)"
        )

    # JOIN/EXISTS 用の橋渡し（なければ追加）
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_gym_equipments_gym_id_equipment_id "
            "ON gym_equipments (gym_id, equipment_id)"
        )

    # equipments.slug は既に BTree を作成済みの想定（未作成なら有効化）
    with op.get_context().autocommit_block():
        op.execute("CREATE INDEX IF NOT EXISTS ix_equipments_slug ON equipments (slug)")


def downgrade():
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX IF EXISTS ix_gyms_pref_city_lvac_desc_id_asc")
        op.execute("DROP INDEX IF EXISTS ix_gym_equipments_gym_id_equipment_id")
        op.execute("DROP INDEX IF EXISTS ix_equipments_slug")
