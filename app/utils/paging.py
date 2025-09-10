# app/utils/paging.py
from __future__ import annotations

import base64
import json

TokenPart = int | str | float


def encode_page_token(*parts: TokenPart) -> str:
    """
    Keyset用のページトークンをJSON→base64でエンコード。
    例: encode_page_token(1726000000, 123) -> "eyJwIjpbMTcyNi4u.."
    """
    payload = {"p": list(parts)}
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_page_token(token: str | None) -> tuple[TokenPart, ...] | None:
    if not token:
        return None
    pad = "=" * (-len(token) % 4)
    raw = base64.urlsafe_b64decode((token + pad).encode("ascii"))
    obj = json.loads(raw.decode("utf-8"))
    parts = obj.get("p", [])
    if not isinstance(parts, list):
        raise ValueError("invalid page token")
    return tuple(parts)


def has_token(token: str | None) -> bool:
    try:
        return decode_page_token(token) is not None
    except Exception:
        return False


def parse_offset_token(token: str | None, *, page: int, per_page: int) -> int:
    """
    既存仕様に合わせて page_token はオフセット整数として扱う。
    token が None の場合は (page-1)*per_page を返す。
    不正な文字列は ValueError を投げる（呼び出し側で 400 に変換）。
    """
    if token is None:
        return (page - 1) * per_page
    # 互換のため純粋な int を期待
    return int(token)


def build_next_offset_token(offset: int, per_page: int, total: int) -> str | None:
    next_offset = offset + per_page
    return str(next_offset) if next_offset < total else None
