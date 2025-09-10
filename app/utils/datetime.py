# app/utils/datetime.py
from __future__ import annotations

from datetime import UTC, datetime


def as_utc_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # UTC へ正規化して tzinfo を剥がす（DB は naive 列）
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def dt_from_token(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        # "Z" を含む場合のフォールバック
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return as_utc_naive(dt)


def dt_to_token(dt: datetime | None) -> str | None:
    dt = as_utc_naive(dt)
    return dt.isoformat(timespec="seconds") if dt else None
