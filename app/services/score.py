from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

FRESH_W = float(os.getenv("SCORE_W_FRESH", "0.6"))
RICH_W = float(os.getenv("SCORE_W_RICH", "0.4"))
WINDOW_DAYS = int(os.getenv("FRESHNESS_WINDOW_DAYS", "365"))

EPS = 1e-6


def _now_naive_utc() -> datetime:
    """Return naive UTC-compatible datetime (consistent with DB naive timestamp handling)."""
    return datetime.utcnow()


def _to_naive_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)


def validate_weights() -> None:
    if abs((FRESH_W + RICH_W) - 1.0) > 1e-6:
        raise ValueError("SCORE weight invalid: SCORE_W_FRESH + SCORE_W_RICH must be 1.0")


def freshness_score(last_verified_at: datetime | None) -> float:
    last_verified_at = _to_naive_utc(last_verified_at)
    if last_verified_at is None:
        return 0.0
    window = timedelta(days=WINDOW_DAYS)
    delta = _now_naive_utc() - last_verified_at
    if delta <= timedelta(0):
        return 1.0
    if delta >= window:
        return 0.0
    return max(0.0, 1.0 - (delta / window))


def richness_score(num_equips: int, max_equips: int) -> float:
    if max_equips <= 0:
        return 0.0
    return max(0.0, min(1.0, num_equips / max_equips))


@dataclass
class ScoreBundle:
    freshness: float
    richness: float
    score: float


def aggregate_score(fresh: float, rich: float) -> float:
    return FRESH_W * fresh + RICH_W * rich


def compute_bundle(
    last_verified_at: datetime | None, num_equips: int, max_equips: int
) -> ScoreBundle:
    f = freshness_score(last_verified_at)
    r = richness_score(num_equips, max_equips)
    return ScoreBundle(f, r, aggregate_score(f, r))
