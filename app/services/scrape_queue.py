from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models.gym_candidate import GymCandidate
from app.services.scrape_utils import scrape_official_url_with_reason

logger = logging.getLogger(__name__)

JobStatus = Literal["queued", "running", "completed"]
ItemStatus = Literal["queued", "success", "failed"]


@dataclass
class ScrapeJobItem:
    candidate_id: int
    status: ItemStatus = "queued"
    failure_reason: str | None = None


@dataclass
class ScrapeJobState:
    job_id: str
    status: JobStatus
    total_count: int
    completed_count: int
    success_count: int
    failure_count: int
    dry_run: bool
    items: dict[int, ScrapeJobItem] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ScrapeTask:
    job_id: str
    candidate_id: int
    dry_run: bool


_queue: asyncio.Queue[ScrapeTask] = asyncio.Queue()
_jobs: dict[str, ScrapeJobState] = {}
_jobs_lock = asyncio.Lock()
_worker_task: asyncio.Task[None] | None = None


def _touch(job: ScrapeJobState) -> None:
    job.updated_at = datetime.now(UTC)


async def start_scrape_worker() -> None:
    global _worker_task
    if _worker_task and not _worker_task.done():
        return
    _worker_task = asyncio.create_task(_worker_loop(), name="scrape-queue-worker")
    logger.info("scrape_queue_worker_started")


async def stop_scrape_worker() -> None:
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        logger.info("scrape_queue_worker_stopped")


async def enqueue_scrape_job(candidate_ids: list[int], *, dry_run: bool) -> ScrapeJobState:
    job_id = str(uuid4())
    items = {cid: ScrapeJobItem(candidate_id=cid) for cid in candidate_ids}
    job = ScrapeJobState(
        job_id=job_id,
        status="queued",
        total_count=len(candidate_ids),
        completed_count=0,
        success_count=0,
        failure_count=0,
        dry_run=dry_run,
        items=items,
    )
    async with _jobs_lock:
        _jobs[job_id] = job
    for cid in candidate_ids:
        await _queue.put(ScrapeTask(job_id=job_id, candidate_id=cid, dry_run=dry_run))
    return job


async def get_scrape_job(job_id: str) -> ScrapeJobState | None:
    async with _jobs_lock:
        return _jobs.get(job_id)


async def _worker_loop() -> None:
    while True:
        task = await _queue.get()
        try:
            await _process_task(task)
        except Exception:
            logger.exception("scrape_queue_task_failed", candidate_id=task.candidate_id)
        finally:
            _queue.task_done()


async def _process_task(task: ScrapeTask) -> None:
    async with _jobs_lock:
        job = _jobs.get(task.job_id)
        if not job:
            logger.warning("scrape_job_missing", job_id=task.job_id)
            return
        if job.status == "queued":
            job.status = "running"
        _touch(job)

    async with SessionLocal() as session:
        result = await session.execute(
            select(GymCandidate)
            .options(selectinload(GymCandidate.source_page))
            .where(GymCandidate.id == task.candidate_id)
        )
        candidate = result.scalar_one_or_none()

        if not candidate:
            await _record_failure(task.job_id, task.candidate_id, "not_found")
            return

        parsed_json = candidate.parsed_json or {}
        official_url = parsed_json.get("official_url")
        scraped_page_url = None
        if candidate.source_page:
            scraped_page_url = candidate.source_page.url

        outcome = await scrape_official_url_with_reason(
            official_url=str(official_url) if official_url else None,
            scraped_page_url=scraped_page_url,
            existing_parsed_json=parsed_json,
        )

        if outcome.merged_data is None:
            await _record_failure(
                task.job_id,
                task.candidate_id,
                outcome.failure_reason or "fetch_failed",
            )
            return

        if not task.dry_run:
            candidate.parsed_json = outcome.merged_data
            session.add(candidate)
            await session.commit()
        else:
            await session.rollback()

        await _record_success(task.job_id, task.candidate_id)


async def _record_success(job_id: str, candidate_id: int) -> None:
    async with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        item = job.items.get(candidate_id)
        if item:
            item.status = "success"
            item.failure_reason = None
        job.completed_count += 1
        job.success_count += 1
        _touch(job)
        if job.completed_count >= job.total_count:
            job.status = "completed"


async def _record_failure(job_id: str, candidate_id: int, reason: str) -> None:
    async with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        item = job.items.get(candidate_id)
        if item:
            item.status = "failed"
            item.failure_reason = reason
        job.completed_count += 1
        job.failure_count += 1
        _touch(job)
        if job.completed_count >= job.total_count:
            job.status = "completed"


def serialize_job(job: ScrapeJobState) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "status": job.status,
        "total_count": job.total_count,
        "completed_count": job.completed_count,
        "success_count": job.success_count,
        "failure_count": job.failure_count,
        "dry_run": job.dry_run,
        "items": [
            {
                "candidate_id": item.candidate_id,
                "status": item.status,
                "failure_reason": item.failure_reason,
            }
            for item in job.items.values()
        ],
    }
