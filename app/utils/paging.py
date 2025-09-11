# app/utils/paging.py
from __future__ import annotations

__all__ = [
    "parse_offset_token",
    "build_next_offset_token",
]


def parse_offset_token(token: str | None, *, page: int, per_page: int) -> int:
    """
    page_token を「オフセット整数」として解釈する互換実装。
    token が None の場合は (page-1)*per_page を返す。
    不正な文字列は ValueError を投げる（呼び出し側で 400 へ変換する想定）。
    """
    if token is None:
        return (page - 1) * per_page
    return int(token)


def build_next_offset_token(offset: int, per_page: int, total_len: int) -> str | None:
    """
    次ページが存在する場合は次オフセット（文字列）を返し、存在しない場合は None を返す。
    - offset: 現在の先頭インデックス
    - per_page: 1ページの件数
    - total_len: ページング対象（pagable）の総件数
    """
    next_offset = offset + per_page
    return str(next_offset) if next_offset < total_len else None
