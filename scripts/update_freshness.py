"""Operations helper to refresh ``gyms.last_verified_at_cached``.

The script resets cached values and re-computes them from
``gym_equipments.last_verified_at`` so that the search scoring reflects the
latest verification status.  It is wired into the ``make freshness`` target and
documented in ``docs/ops_geocode_and_freshness.md``.
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

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


async def update_freshness(async_engine: AsyncEngine | None = None) -> dict[str, int]:
    """Recompute cached freshness timestamps and return an execution summary."""

    engine_to_use = async_engine or engine
    async with engine_to_use.begin() as conn:
        r1 = await conn.execute(RESET_SQL)
        r2 = await conn.execute(UPDATE_SQL)
        # rowcount can be None on some drivers; guard with or 0
        reset_rows = r1.rowcount or 0
        updated_rows = r2.rowcount or 0
    return {"reset_rows": reset_rows, "updated_rows": updated_rows}


async def main() -> int:
    summary = await update_freshness()
    print(
        "✅ reset rows: {reset_rows}, updated rows: {updated_rows}".format(
            reset_rows=summary["reset_rows"],
            updated_rows=summary["updated_rows"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
