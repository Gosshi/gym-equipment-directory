"""Approve normalized gym candidates and upsert data into main tables."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.services.approve_service import (
    ApprovalError,
    ApproveService,
    CandidateNotFoundError,
    CandidateStatusConflictError,
)

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@dataclass(slots=True)
class ApprovalBatchItem:
    candidate_id: int
    dry_run: bool
    success: bool
    payload: dict[str, Any] | None = None
    error: str | None = None


def _log_payload(payload: dict[str, Any]) -> None:
    message = json.dumps(payload, ensure_ascii=False)
    if payload.get("error"):
        logger.warning("Approval completed with warnings: %s", payload["error"])
    logger.info("Approval result: %s", message)


async def run_approval_batch(
    candidate_ids: Sequence[int],
    dry_run: bool,
    *,
    session_factory: SessionFactory | None = None,
) -> list[ApprovalBatchItem]:
    if not candidate_ids:
        raise ValueError("candidate_ids must not be empty")
    factory = session_factory or SessionLocal
    results: list[ApprovalBatchItem] = []
    async with factory() as session:
        service = ApproveService(session)
        for candidate_id in candidate_ids:
            try:
                response = await service.approve(candidate_id, dry_run=dry_run)
            except CandidateNotFoundError:
                logger.error("Candidate %s not found", candidate_id)
                results.append(
                    ApprovalBatchItem(
                        candidate_id=candidate_id,
                        dry_run=dry_run,
                        success=False,
                        error="candidate not found",
                    )
                )
                continue
            except CandidateStatusConflictError as exc:
                logger.error("Candidate %s already processed: %s", candidate_id, exc)
                results.append(
                    ApprovalBatchItem(
                        candidate_id=candidate_id,
                        dry_run=dry_run,
                        success=False,
                        error=str(exc),
                    )
                )
                continue
            except ApprovalError as exc:
                logger.error("Approval failed for candidate %s: %s", candidate_id, exc)
                results.append(
                    ApprovalBatchItem(
                        candidate_id=candidate_id,
                        dry_run=dry_run,
                        success=False,
                        error=str(exc),
                    )
                )
                continue

            payload = response.to_dict()
            _log_payload(payload)
            results.append(
                ApprovalBatchItem(
                    candidate_id=candidate_id,
                    dry_run=dry_run,
                    success=True,
                    payload=payload,
                )
            )
    return results


async def approve_candidates(candidate_ids: Sequence[int], dry_run: bool) -> int:
    """Approve multiple candidates sequentially."""

    results = await run_approval_batch(candidate_ids, dry_run=dry_run)
    failures = [item for item in results if not item.success]
    return 0 if not failures else 1


async def approve_candidate(candidate_id: int, dry_run: bool) -> int:
    """Approve a single candidate for backward-compatible CLI usage."""

    return await approve_candidates([candidate_id], dry_run=dry_run)


__all__ = [
    "approve_candidate",
    "approve_candidates",
    "run_approval_batch",
]
