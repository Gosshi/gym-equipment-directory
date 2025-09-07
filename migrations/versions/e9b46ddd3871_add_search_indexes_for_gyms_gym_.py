"""add search indexes for gyms & gym_equipments

Revision ID: e9b46ddd3871
Revises: 4965b1c2c229
Create Date: 2025-09-05 21:42:28.603609

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e9b46ddd3871"
down_revision = "4965b1c2c229"
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------
    # gym_equipments の複合インデックス（順序違いで 2 本）
    #  - 検索条件や JOIN の方向に応じて使い分けられるように
    # ------------------------------------------------------------
    # Alembic の op.create_index(postgresql_concurrently=True) は
    # migration を非トランザクション化する必要があるため、
    # ここでは autocommit_block + 生SQLを使います。
    with op.get_context().autocommit_block():
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_gym_equipments_equipment_id_gym_id
            ON gym_equipments (equipment_id, gym_id)
        """)
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_gym_equipments_gym_id_equipment_id
            ON gym_equipments (gym_id, equipment_id)
        """)

        # --------------------------------------------------------
        # gyms.last_verified_at_cached の降順・部分インデックス
        # - NULL を除外 (WHERE last_verified_at_cached IS NOT NULL)
        # - 並び替え最適化のため DESC 指定
        # --------------------------------------------------------
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_gyms_last_verified_at_cached_desc_notnull
            ON gyms (last_verified_at_cached DESC)
            WHERE last_verified_at_cached IS NOT NULL
        """)


def downgrade():
    # 可能なら DROP INDEX CONCURRENTLY にするため autocommit_block
    with op.get_context().autocommit_block():
        op.execute("""
            DROP INDEX IF EXISTS ix_gyms_last_verified_at_cached_desc_notnull
        """)
        op.execute("""
            DROP INDEX IF EXISTS ix_gym_equipments_gym_id_equipment_id
        """)
        op.execute("""
            DROP INDEX IF EXISTS ix_gym_equipments_equipment_id_gym_id
        """)
