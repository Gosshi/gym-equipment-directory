# scripts/update_freshness.py
"""
gyms.last_verified_at_cached を一括更新するユーティリティ。
- すべてのジムをいったん NULL にリセット
- gym_equipments の MAX(last_verified_at) をキャッシュに反映
"""

import asyncio

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


async def main() -> int:
    async with engine.begin() as conn:
        r1 = await conn.execute(RESET_SQL)
        r2 = await conn.execute(UPDATE_SQL)
        # rowcount can be None on some drivers; guard with or 0
        reset_rows = r1.rowcount or 0
        updated_rows = r2.rowcount or 0
        print(f"✅ reset rows: {reset_rows}, updated rows: {updated_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
