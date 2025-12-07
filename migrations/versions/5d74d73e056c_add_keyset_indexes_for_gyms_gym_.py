"""add keyset indexes for gyms/gym_equipments/equipments

Revision ID: 5d74d73e056c
Revises: 784e740115be
Create Date: 2025-09-06 12:18:13.075591

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d74d73e056c"
down_revision: str | None = "784e740115be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    # 既存掃除（制約→インデックスの順で）
    op.execute("ALTER TABLE equipments DROP CONSTRAINT IF EXISTS uq_equipments_slug")
    op.execute("DROP INDEX IF EXISTS ix_equipments_id")
    op.execute("DROP INDEX IF EXISTS ix_equipments_slug")
    # op.execute("DROP INDEX IF EXISTS ix_equipments_slug_trgm")  # 使わないなら

    # ここに gyms / gym_equipments の create_index が続く想定
    op.create_index(
        "ix_gyms_pref_city_lvac_id",
        "gyms",
        ["pref", "city", sa.text("last_verified_at_cached DESC NULLS LAST"), sa.text("id ASC")],
        unique=False,
    )
    op.create_index(
        "ix_gym_equipments_gym_equipment",
        "gym_equipments",
        ["gym_id", "equipment_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_gym_equipments_gym_equipment", table_name="gym_equipments")
    op.drop_index("ix_gyms_pref_city_lvac_id", table_name="gyms")
