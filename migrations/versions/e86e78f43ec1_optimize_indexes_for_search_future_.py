"""optimize indexes for search & future keyset

Revision ID: e86e78f43ec1
Revises: 7bbc5b5e9bb5
Create Date: 2025-09-06 00:08:10.251969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e86e78f43ec1'
down_revision: Union[str, None] = '7bbc5b5e9bb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) equipments.slug へ非ユニーク索引（重複がある環境でも安全に適用可能）
    #    後日データクレンジングが済んだら UNIQUE 化を検討
    op.create_index(
        "ix_equipments_slug",
        "equipments",
        ["slug"],
        unique=False,
        postgresql_using="btree",
    )

    # 2) freshness用に複合・部分インデックス（キーセットページング予定）
    op.create_index(
        "ix_gyms_last_verified_id_partial",
        "gyms",
        ["last_verified_at_cached", "id"],
        unique=False,
        postgresql_where=sa.text("last_verified_at_cached IS NOT NULL"),
        postgresql_using="btree",
    )


def downgrade():
    op.drop_index("ix_gyms_last_verified_id_partial", table_name="gyms")
    op.drop_index("ix_equipments_slug", table_name="equipments")
