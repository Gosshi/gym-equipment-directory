from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

FRESH_W = float(os.getenv("SCORE_W_FRESH", "0.6"))
RICH_W = float(os.getenv("SCORE_W_RICH", "0.4"))
WINDOW_DAYS = int(os.getenv("FRESHNESS_WINDOW_DAYS", "365"))

EPS = 1e-6


def _now() -> datetime:
    return datetime.now(UTC)


def validate_weights() -> None:
    """起動時検証用。合計 1.0±ε を要求。"""
    if abs((FRESH_W + RICH_W) - 1.0) > 1e-6:
        raise ValueError(
            f"SCORE weight invalid: SCORE_W_FRESH + SCORE_W_RICH must be 1.0 "
            f"(got {FRESH_W + RICH_W:.6f})"
        )
    if FRESH_W < -EPS or RICH_W < -EPS:
        raise ValueError("SCORE weights must be non-negative")


def freshness_score(last_verified_at: datetime | None) -> float:
    """last_verified_at が None の場合は 0。WINDOW_DAYS で線形減衰。"""
    if last_verified_at is None:
        return 0.0
    window = timedelta(days=WINDOW_DAYS)
    delta = _now() - last_verified_at
    if delta <= timedelta(0):
        return 1.0
    if delta >= window:
        return 0.0
    # 1 → 0 の線形
    return max(0.0, 1.0 - (delta / window))


def richness_score(num_equips: int, max_equips: int) -> float:
    """設備充実度の正規化（0..1）。max_equips==0 は 0 とする。"""
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
    last_verified_at: datetime | None,
    num_equips: int,
    max_equips: int,
) -> ScoreBundle:
    f = freshness_score(last_verified_at)
    r = richness_score(num_equips, max_equips)
    return ScoreBundle(f, r, aggregate_score(f, r))
