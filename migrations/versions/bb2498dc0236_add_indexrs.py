"""add_indexrs

Revision ID: bb2498dc0236
Revises: 5d74d73e056c
Create Date: 2025-09-10 21:50:03.288860

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bb2498dc0236"
down_revision: str | None = "5d74d73e056c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.execute("""
      CREATE INDEX IF NOT EXISTS idx_gyms_pref_city
      ON gyms (pref, city);
    """)
    op.execute("""
      CREATE INDEX IF NOT EXISTS idx_gyms_fresh_id_desc
      ON gyms (last_verified_at_cached DESC, id DESC);
    """)
    op.execute("""
      CREATE INDEX IF NOT EXISTS idx_gym_equipments_gym_id
      ON gym_equipments (gym_id);
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_gyms_pref_city;")
    op.execute("DROP INDEX IF EXISTS idx_gyms_fresh_id_desc;")
    op.execute("DROP INDEX IF EXISTS idx_gym_equipments_gym_id;")
