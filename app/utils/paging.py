# app/utils/paging.py
from __future__ import annotations

__all__ = [
    "parse_offset_token",
    "build_next_offset_token",
]


def parse_offset_token(
    token: str | None,
    *,
    page: int,
    per_page: int,
    expected_sort_key: str | None = None,
) -> int:
    """page_token をオフセット整数に復号する。

    サポート形式:
    1. レガシー: 純整数文字列 (例: "40")
    2. 拡張形式: "<offset>:<h>"
        - <h>: ソートキー等の短縮ハッシュ

    注意:
    - token が None の場合は `(page-1)*per_page` を採用。
    - 空文字や不正フォーマット、ソートキー不一致は ValueError を送出し、呼び出し
      側で 400/422 に変換する想定。
    セキュリティ:
    - int() 変換時に過大値（極端に大きいオフセット）が来る可能性: 呼び出し側で最大ページ防御を推奨。
    """
    if token is None:
        return (page - 1) * per_page

    token = token.strip()
    if not token:
        raise ValueError("empty page_token")

    raw = token
    hash_part: str | None = None
    if ":" in token:
        raw, hash_part = token.split(":", 1)
        if not raw:
            raise ValueError("empty page_token")

    offset = int(raw)
    if offset < 0:
        raise ValueError("invalid page_token")

    if expected_sort_key and hash_part:
        expected_hash = expected_sort_key[:8]
        if hash_part != expected_hash:
            raise ValueError("invalid page_token")

    return offset


def build_next_offset_token(
    offset: int,
    per_page: int,
    total_len: int,
    *,
    sort_key: str | None = None,
) -> str | None:
    """次ページが存在する場合に前進用の page_token を生成する。

    仕様:
    - 返却形式: "<next_offset>:<hash>"（<hash> は sort_key の先頭 8 文字。将来ハッシュ化差し替え可）
    - 次ページが存在しない場合は None を返す。
    目的:
    - sort_key 埋め込み: ソート変更後の旧トークン誤用検出を容易化（厳密検証は呼び出し側拡張）。
    拡張余地:
    - ハッシュ衝突耐性を高めるため SHA1/XXHash などへ置換。
    - Keyset 移行時: オフセットではなく境界キー（例: timestamp,id）を token に含める形へ拡張予定。
    """
    next_offset = offset + per_page
    if next_offset >= total_len:
        return None
    if not sort_key:
        # 後方互換: sort_key 未指定時は純整数形式
        return str(next_offset)
    h = sort_key[:8]
    return f"{next_offset}:{h}"
