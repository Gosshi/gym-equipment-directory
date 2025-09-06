"""constraints_indexes_cached_freshness

Revision ID: 5c002a33eee9
Revises: 7373a9796dd6
Create Date: 2025-09-04 13:13:17.153348
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5c002a33eee9'
down_revision: Union[str, None] = '7373a9796dd6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 一意制約（既に存在する可能性があるため DO ブロックで保護） ---
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_gyms_slug'
      ) THEN
        ALTER TABLE gyms ADD CONSTRAINT uq_gyms_slug UNIQUE (slug);
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_equipments_slug'
      ) THEN
        ALTER TABLE equipments ADD CONSTRAINT uq_equipments_slug UNIQUE (slug);
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_gym_equipment_pair'
      ) THEN
        ALTER TABLE gym_equipments ADD CONSTRAINT uq_gym_equipment_pair UNIQUE (gym_id, equipment_id);
      END IF;
    END $$;
    """)

    # --- チェック制約（存在チェック付き） ---
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_gym_eq_count_nonneg'
      ) THEN
        ALTER TABLE gym_equipments
          ADD CONSTRAINT ck_gym_eq_count_nonneg CHECK (count IS NULL OR count >= 0);
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_gym_eq_maxw_nonneg'
      ) THEN
        ALTER TABLE gym_equipments
          ADD CONSTRAINT ck_gym_eq_maxw_nonneg CHECK (max_weight_kg IS NULL OR max_weight_kg >= 0);
      END IF;
    END $$;
    """)

    # --- インデックス（IF NOT EXISTS が使えるものは活用） ---
    op.execute("CREATE INDEX IF NOT EXISTS ix_gyms_pref_city ON gyms (prefecture, city);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gym_eq_gym ON gym_equipments (gym_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gym_eq_eq ON gym_equipments (equipment_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gym_eq_last_verified ON gym_equipments (last_verified_at);")
    # 部分インデックス（Enumはtextにキャストしておくと頑健）
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_gym_eq_present "
        "ON gym_equipments (gym_id) WHERE availability = 'present';"
    )

    # 鮮度キャッシュ列
    with op.batch_alter_table("gyms") as batch_op:
        batch_op.add_column(sa.Column("last_verified_at_cached", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # 逆順で削除

    # 鮮度キャッシュ列
    with op.batch_alter_table("gyms") as batch_op:
        batch_op.drop_column("last_verified_at_cached")

    # インデックス
    op.execute("DROP INDEX IF EXISTS ix_gym_eq_present;")
    op.execute("DROP INDEX IF EXISTS ix_gym_eq_last_verified;")
    op.execute("DROP INDEX IF EXISTS ix_gym_eq_eq;")
    op.execute("DROP INDEX IF EXISTS ix_gym_eq_gym;")
    op.execute("DROP INDEX IF EXISTS ix_gyms_pref_city;")

    # チェック制約
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_gym_eq_maxw_nonneg') THEN
        ALTER TABLE gym_equipments DROP CONSTRAINT ck_gym_eq_maxw_nonneg;
      END IF;
      IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_gym_eq_count_nonneg') THEN
        ALTER TABLE gym_equipments DROP CONSTRAINT ck_gym_eq_count_nonneg;
      END IF;
    END $$;
    """)

    # 一意制約
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_gym_equipment_pair') THEN
        ALTER TABLE gym_equipments DROP CONSTRAINT uq_gym_equipment_pair;
      END IF;
      IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_equipments_slug') THEN
        ALTER TABLE equipments DROP CONSTRAINT uq_equipments_slug;
      END IF;
      IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_gyms_slug') THEN
        ALTER TABLE gyms DROP CONSTRAINT uq_gyms_slug;
      END IF;
    END $$;
    """)
