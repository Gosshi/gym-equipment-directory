"""Batch ingest pipeline minimal tests.

目的:
    - dry-run 実行が 0 を返す
    - return_metrics=True でメトリクス dict を受け取れる

依存:
    DB接続を避けるため対象関数を monkeypatch でスタブ化
"""

from __future__ import annotations

import pytest

from scripts.ingest import pipeline


@pytest.mark.asyncio
async def test_run_batch_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ok(*args, **kwargs):  # noqa: D401 - テスト用簡易スタブ
        return 0

    async def _classify(session, *, source: str, candidate_ids):  # noqa: D401
        from scripts.ingest.diff import DiffSummary

        return DiffSummary(new_ids=(1, 2), updated_ids=(), duplicate_ids=(), reviewing_ids=())

    monkeypatch.setattr("scripts.ingest.pipeline.fetch_http_pages", _ok)
    monkeypatch.setattr("scripts.ingest.pipeline.parse_pages", _ok)
    monkeypatch.setattr("scripts.ingest.pipeline.normalize_candidates", _ok)
    monkeypatch.setattr("scripts.ingest.pipeline.classify_candidates", _classify)
    monkeypatch.setattr("scripts.ingest.pipeline.approve_candidates", _ok)

    status = await pipeline.run_batch(
        source="dummy",
        pref="tokyo",
        city="koto",
        limit=5,
        dry_run=True,
        max_retries=None,
        timeout=5.0,
        min_delay=0.1,
        max_delay=0.2,
        respect_robots=False,
        user_agent="test-agent",
        force=False,
    )
    assert status == 0


@pytest.mark.asyncio
async def test_run_batch_return_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ok(*args, **kwargs):
        return 0

    async def _classify(session, *, source: str, candidate_ids):  # noqa: D401
        from scripts.ingest.diff import DiffSummary

        return DiffSummary(new_ids=(42,), updated_ids=(), duplicate_ids=(), reviewing_ids=())

    monkeypatch.setattr("scripts.ingest.pipeline.fetch_http_pages", _ok)
    monkeypatch.setattr("scripts.ingest.pipeline.parse_pages", _ok)
    monkeypatch.setattr("scripts.ingest.pipeline.normalize_candidates", _ok)
    monkeypatch.setattr("scripts.ingest.pipeline.classify_candidates", _classify)
    monkeypatch.setattr("scripts.ingest.pipeline.approve_candidates", _ok)

    status, metrics = pipeline.run_batch.__wrapped__(  # type: ignore[attr-defined]
        source="dummy",
        pref="tokyo",
        city="koto",
        limit=5,
        dry_run=True,
        max_retries=None,
        timeout=5.0,
        min_delay=0.1,
        max_delay=0.2,
        respect_robots=False,
        user_agent="test-agent",
        force=False,
        return_metrics=True,
    )  # Returns tuple
    assert status == 0
    assert isinstance(metrics, dict)
    assert metrics["counters"]["approve_targets"] == 1
