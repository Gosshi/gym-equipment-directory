"""シンプルなメトリクス収集器。

要件:
    - カウンタ加算 add(event, value=1)
    - タイマー (context manager) time(label)
    - export() で dict 返却 -> ログ/外部送信準備

将来拡張:
    - Prometheus / StatsD エミッタ
    - ヒストグラム/分位数
"""

from __future__ import annotations

import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class MetricsSnapshot:
    counters: dict[str, int]
    timings: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {"counters": dict(self.counters), "timings": dict(self.timings)}


class MetricsCollector:
    def __init__(self) -> None:
        self._counters: defaultdict[str, int] = defaultdict(int)
        self._timings: dict[str, float] = {}

    def add(self, name: str, value: int = 1) -> None:
        self._counters[name] += value

    @contextmanager
    def time(self, name: str):  # type: ignore[override]
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self._timings[name] = elapsed

    def export(self) -> MetricsSnapshot:
        snapshot = MetricsSnapshot(counters=dict(self._counters), timings=dict(self._timings))
        logger.info("Metrics export", snapshot=snapshot.to_dict())
        return snapshot


__all__ = ["MetricsCollector", "MetricsSnapshot"]
