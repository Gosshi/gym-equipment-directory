"""Batch ingestion orchestrator.

段階:
    1. fetch-http (HTTPスクレイプ)
    2. parse (HTML -> gym_candidates)
    3. normalize (候補正規化 / 住所・設備フィルタ / ジオコーディング任意)
    4. diff (新規 / 更新 / 重複分類) ※初期はスタブ
    5. approve (new + updated を本テーブルへ反映) ※dry-runでskip

設計ポリシー:
    - 各フェーズは既存関数を呼び出し、戻り値ステータスコード(0=成功)のみを確認
    - 失敗は例外を投げ「全体を失敗」とする (将来: 部分再実行サポート)
    - メトリクスは最終的にログへ出力し、オプションで呼び出し側へ返却

環境変数 (予定):
    INGEST_BATCH_GEOCODE_MISSING=true/false

TODO (後続PR):
    - diff分類の実装 (DB比較)
    - approve 対象フィルタリング (重複除外 / 更新のみ)
    - 冪等性トラッキング (前回実行ID保存)
"""

from __future__ import annotations

import gc
import logging
from typing import Any

from sqlalchemy import select

from app.db import SessionLocal  # noqa: I001
from app.models.gym_candidate import CandidateStatus, GymCandidate  # noqa: I001

from .approve import approve_candidates
from .diff import classify_candidates
from .fetch_http import fetch_http_pages
from .metrics import MetricsCollector
from .normalize import normalize_candidates
from .parse import parse_pages

logger = logging.getLogger(__name__)


async def _list_candidate_ids(session, source: str) -> list[int]:
    result = await session.execute(
        select(GymCandidate.id, GymCandidate.status).order_by(GymCandidate.id.desc())
    )
    rows = result.all()
    # 初期版では status=new のみ承認候補とみなす
    return [row[0] for row in rows if row[1] == CandidateStatus.new]


async def run_batch(
    *,
    source: str,
    pref: str,
    city: str,
    limit: int,
    dry_run: bool,
    max_retries: int | None,
    timeout: float,
    min_delay: float,
    max_delay: float,
    respect_robots: bool,
    user_agent: str,
    force: bool,
    return_metrics: bool = False,
) -> int | tuple[int, dict[str, Any]]:
    metrics = MetricsCollector()

    # 1. fetch
    with metrics.time("fetch_http"):
        code = await fetch_http_pages(
            source,
            pref=pref,
            city=city,
            limit=limit,
            min_delay=min_delay,
            max_delay=max_delay,
            respect_robots=respect_robots,
            user_agent=user_agent,
            timeout=timeout,
            dry_run=dry_run,
            force=force,
        )
    if code != 0:
        raise RuntimeError(f"fetch_http failed with code={code}")
    gc.collect()

    # 2. parse
    with metrics.time("parse"):
        code = await parse_pages(source, limit=None)
    if code != 0:
        raise RuntimeError(f"parse failed with code={code}")
    gc.collect()

    # 3. normalize
    with metrics.time("normalize"):
        code = await normalize_candidates(source, limit=None, geocode_missing=False)
    if code != 0:
        raise RuntimeError(f"normalize failed with code={code}")
    gc.collect()

    # 4. diff classification
    async with SessionLocal() as session:
        candidate_ids = await _list_candidate_ids(session, source)
        metrics.add("candidates_after_normalize", len(candidate_ids))
        with metrics.time("diff_classify"):
            diff_summary = await classify_candidates(
                session,
                source=source,
                candidate_ids=candidate_ids,
            )
        metrics.add("diff_new", len(diff_summary.new_ids))
        metrics.add("diff_updated", len(diff_summary.updated_ids))
        metrics.add("diff_duplicates", len(diff_summary.duplicate_ids))

    # 5. approve (skip duplicates; updatedは現時点 new 同等扱い)
    approve_target_ids = list(diff_summary.new_ids) + list(diff_summary.updated_ids)
    metrics.add("approve_targets", len(approve_target_ids))

    if dry_run:
        logger.info("Dry-run: approval skipped (targets=%s)", approve_target_ids)
        metrics.add("approved", 0)
    else:
        with metrics.time("approve"):
            if approve_target_ids:
                code = await approve_candidates(approve_target_ids, dry_run=False)
                if code != 0:
                    raise RuntimeError(f"approve failed with code={code}")
                metrics.add("approved", len(approve_target_ids))
            else:
                metrics.add("approved", 0)

    snapshot = metrics.export().to_dict()
    logger.info("Batch pipeline completed", metrics=snapshot)
    if return_metrics:
        return 0, snapshot
    return 0


__all__ = ["run_batch"]
