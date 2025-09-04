# scripts/update_freshness.py
"""
gyms.last_verified_at_cached を一括更新するユーティリティ。
- すべてのジムをいったん NULL にリセット
- gym_equipments の MAX(last_verified_at) をキャッシュに反映
"""

from sqlalchemy import text
from app.db import engine

RESET_SQL = text("""
UPDATE gyms
SET last_verified_at_cached = NULL
""")

UPDATE_SQL = text("""
UPDATE gyms AS g
SET last_verified_at_cached = sub.max_lv
FROM (
  SELECT gym_id, MAX(last_verified_at) AS max_lv
  FROM gym_equipments
  WHERE last_verified_at IS NOT NULL
  GROUP BY gym_id
) AS sub
WHERE g.id = sub.gym_id
""")

def main() -> int:
    with engine.begin() as conn:
        r1 = conn.execute(RESET_SQL)
        r2 = conn.execute(UPDATE_SQL)
        print(f"✅ reset rows: {r1.rowcount}, updated rows: {r2.rowcount}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
