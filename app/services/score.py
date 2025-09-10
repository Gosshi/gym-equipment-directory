from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import TypedDict

FRESH_W = float(os.getenv("SCORE_W_FRESH", "0.6"))
RICH_W = float(os.getenv("SCORE_W_RICH", "0.4"))
WINDOW_DAYS = int(os.getenv("FRESHNESS_WINDOW_DAYS", "365"))


class ScoreBundle(TypedDict):
    freshness: float
    richness: float
    score: float


def _to_naive_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)


def freshness_score(last_verified_at: datetime | None) -> float:
    last = _to_naive_utc(last_verified_at)
    if last is None:
        return 0.0
    now = datetime.utcnow()
    window = timedelta(days=WINDOW_DAYS)
    delta = now - last
    if delta <= timedelta(0):
        return 1.0
    if delta >= window:
        return 0.0
    return max(0.0, 1.0 - (delta / window))


def richness_score(num_equips: int, max_equips: int) -> float:
    if max_equips <= 0:
        return 0.0
    return max(0.0, min(1.0, num_equips / max_equips))


def compute_bundle(
    last_verified_at: datetime | None, num_equips: int, max_equips: int
) -> ScoreBundle:
    f = freshness_score(last_verified_at)
    r = richness_score(num_equips, max_equips)
    s = FRESH_W * f + RICH_W * r
    return {"freshness": f, "richness": r, "score": s}
