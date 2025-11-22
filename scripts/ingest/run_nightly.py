"""Nightly batch runner for municipal ingest pipelines using subprocess isolation."""

from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os
import time
from collections.abc import Mapping

from dotenv import load_dotenv

from app.db import configure_engine

from .fetch_http import DEFAULT_MAX_DELAY, DEFAULT_MIN_DELAY, DEFAULT_USER_AGENT
from .pipeline import run_batch

logger = logging.getLogger(__name__)

TARGETS: tuple[Mapping[str, str], ...] = (
    {"source": "municipal_edogawa", "pref": "tokyo", "city": "edogawa"},
    {"source": "municipal_koto", "pref": "tokyo", "city": "koto"},
    {"source": "municipal_sumida", "pref": "tokyo", "city": "sumida"},
    {"source": "municipal_tokyo_metropolitan", "pref": "tokyo", "city": "tokyo-metropolitan"},
)

ASYNC_TIMEOUT = 300.0  # 5分 (少し長めに)


def _worker_process(target: Mapping[str, str], db_url: str | None) -> None:
    """Run a single batch in a separate process to ensure memory cleanup."""

    # サブプロセス内で設定を初期化
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    if db_url:
        configure_engine(db_url)

    source = target["source"]
    pref = target["pref"]
    city = target["city"]

    logger.info(f"--- Subprocess started for {source} ---")

    try:
        # 非同期処理を実行するためのイベントループを作成
        asyncio.run(
            run_batch(
                source=source,
                pref=pref,
                city=city,
                limit=None,
                dry_run=False,
                max_retries=None,
                timeout=ASYNC_TIMEOUT,
                min_delay=DEFAULT_MIN_DELAY,
                max_delay=DEFAULT_MAX_DELAY,
                respect_robots=True,
                user_agent=DEFAULT_USER_AGENT,
                force=False,
            )
        )
        logger.info(f"--- Subprocess finished for {source} ---")
    except Exception:
        logger.exception(f"--- Subprocess FAILED for {source} ---")
        raise  # 親プロセスに失敗を伝える（exit code 1になる）


def run_all_targets() -> int:
    """Run all targets sequentially, each in a fresh process."""
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    had_failures = False

    for target in TARGETS:
        source = target["source"]
        logger.info(f"Spawning process for target: {source}")

        # プロセス作成 (fork/spawn)
        p = multiprocessing.Process(target=_worker_process, args=(target, db_url))
        p.start()
        p.join()  # 終了を待つ

        if p.exitcode != 0:
            logger.error(f"Target {source} failed with exit code {p.exitcode}")
            had_failures = True
        else:
            logger.info(f"Target {source} completed successfully.")

        # 念のため少しクールダウン（DB接続数などの安定化のため）
        time.sleep(2)

    return 1 if had_failures else 0


if __name__ == "__main__":
    raise SystemExit(run_all_targets())
