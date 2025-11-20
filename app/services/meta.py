"""メタデータ取得サービス。

PR-09 要件:
1. セレクタ用メタ API: /meta/prefectures, /meta/cities, /meta/categories
2. 後方互換: 旧キー(pref/city/category/slug/name)は computed_field で維持（schemas/meta.py）。
3. キャッシュ戦略: シンプルなインメモリ TTL キャッシュを実装し、環境変数 `META_CACHE_TTL_SECONDS`
   で TTL を制御（デフォルト 300 秒）。Redis 等への差し替え余地をコメントで明示。
4. エラー形状: HTTPException を利用し既存 API の detail 形状を踏襲。

キャッシュ方針:
- サイズは極小（文字列リスト）なのでプロセス内 dict で十分。
- TTL 経過後の参照は再フェッチし置換。
- 失敗時（SQLAlchemyError）はキャッシュ更新せず古い値は保持しない（安全側: 常に再試行）。
- 無効化は TTL のみ。管理者操作や更新頻度が高くないため flush API は未提供。

将来の拡張:
- 抽象インターフェース(ICacheBackend)を追加し RedisBackend / MemoryBackend 実装で差し替え可能。
"""

from __future__ import annotations

import os
import time
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Gym
from app.repositories.meta_repository import MetaRepository

# ---- In-memory TTL cache (process local) ----
_META_CACHE: dict[str, tuple[float, Any]] = {}
_META_CACHE_TTL = int(os.getenv("META_CACHE_TTL_SECONDS", "300"))


def _cache_get(key: str) -> Any | None:
    entry = _META_CACHE.get(key)
    if not entry:
        return None
    ts, value = entry
    if time.time() - ts > _META_CACHE_TTL:
        return None  # expired
    return value


def _cache_set(key: str, value: Any) -> None:
    _META_CACHE[key] = (time.time(), value)


class MetaService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = MetaRepository(session)

    async def list_pref_options(self) -> list[dict]:
        cache_key = "pref_options"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
        try:
            stmt = (
                select(
                    Gym.pref.label("pref"),
                    func.count().label("count"),
                )
                .where(Gym.pref != "")
                .group_by(Gym.pref)
                .order_by(func.count().desc(), Gym.pref.asc())
            )
            rows = (await self._session.execute(stmt)).mappings().all()
            out = [{"key": r["pref"], "label": r["pref"], "count": int(r["count"])} for r in rows]
            _cache_set(cache_key, out)
            return out
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="database unavailable")

    async def list_city_options(self, pref: str) -> list[dict]:
        pref_norm = pref.lower()
        cache_key = f"city_options:{pref_norm}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
        try:
            exists_count = await self._session.scalar(
                select(func.count()).select_from(Gym).where(Gym.pref == pref_norm)
            )
            if not exists_count:
                raise HTTPException(status_code=404, detail="pref not found")

            stmt = (
                select(
                    Gym.city.label("city"),
                    func.count().label("count"),
                )
                .where(Gym.pref == pref_norm, Gym.city != "")
                .group_by(Gym.city)
                .order_by(func.count().desc(), Gym.city.asc())
            )
            rows = (await self._session.execute(stmt)).mappings().all()
            out = [{"key": r["city"], "label": r["city"], "count": int(r["count"])} for r in rows]
            _cache_set(cache_key, out)
            return out
        except HTTPException:
            raise
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="database unavailable")

    async def list_category_options(self) -> list[dict[str, str | None]]:
        """Return distinct equipment categories with stable keys.

        count は現状 None 固定。キャッシュキー: category_options
        """

        cache_key = "category_options"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
        try:
            categories = await self._repo.list_distinct_equipment_categories()
            out = [{"key": c, "label": c, "count": None} for c in categories]
            _cache_set(cache_key, out)
            return out
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="database unavailable")

    async def list_prefectures(self) -> list[dict[str, str | None]]:
        """Return distinct prefecture slugs (non-empty)."""

        try:
            prefs = await self._repo.list_distinct_prefs()
            return [{"key": p, "label": p} for p in prefs]
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="database unavailable")

    async def list_cities_distinct(self, pref: str) -> list[dict[str, str | None]]:
        """Return distinct city slugs for a prefecture (non-empty)."""

        try:
            cities = await self._repo.list_distinct_cities(pref)
            return [{"key": c, "label": c} for c in cities]
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="database unavailable")

    async def list_equipments(self) -> list[dict[str, str | None]]:
        """Return equipment options used for search filters."""

        try:
            results = await self._repo.list_equipment_options()
            return [
                {
                    "key": r.get("slug"),
                    "label": r.get("name") or r.get("slug"),
                    "category": r.get("category"),
                }
                for r in results
            ]
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="database unavailable")
