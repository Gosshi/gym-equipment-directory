# app/utils/paging.py
from __future__ import annotations

__all__ = [
    "parse_offset_token",
    "build_next_offset_token",
]


def parse_offset_token(token: str | None, *, page: int, per_page: int) -> int:
    """Decode a paging token into an integer offset.

    Accepts two formats:
    1. Legacy: plain integer string (e.g. "40")
    2. Extended: "<offset>:<h>" where <h> is a short hash / sort discriminator

    Unknown / malformed tokens raise ValueError (caller converts to HTTP 400/422).
    """
    if token is None:
        return (page - 1) * per_page
    token = token.strip()
    if not token:
        raise ValueError("empty page_token")
    if ":" in token:
        raw, _hash = token.split(":", 1)
        return int(raw)
    return int(token)


def build_next_offset_token(
    offset: int,
    per_page: int,
    total_len: int,
    *,
    sort_key: str | None = None,
) -> str | None:
    """Generate a forward paging token if more items remain.

    The token encodes the *next* offset plus an optional sort discriminator to
    reduce accidental reuse after a client changes its sort key.

    Format: "<next_offset>:<hash>" (hash truncated to 8 chars). If no more
    results remain, returns ``None``.
    """
    next_offset = offset + per_page
    if next_offset >= total_len:
        return None
    h = (sort_key or "")[:8]
    return f"{next_offset}:{h}"
