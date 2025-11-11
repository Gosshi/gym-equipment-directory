"""Approve normalized gym candidates and upsert data into main tables."""

from __future__ import annotations

import json
import logging

from app.db import SessionLocal
from app.services.approve_service import (
    ApprovalError,
    ApproveService,
    CandidateNotFoundError,
    CandidateStatusConflictError,
)

logger = logging.getLogger(__name__)


async def approve_candidate(candidate_id: int, dry_run: bool) -> int:
    """Approve a candidate and return zero on success."""

    async with SessionLocal() as session:
        service = ApproveService(session)
        try:
            result = await service.approve(candidate_id, dry_run=dry_run)
        except CandidateNotFoundError:
            logger.error("Candidate %s not found", candidate_id)
            return 1
        except CandidateStatusConflictError as exc:
            logger.error("Candidate %s already processed: %s", candidate_id, exc)
            return 1
        except ApprovalError as exc:
            logger.error("Approval failed for candidate %s: %s", candidate_id, exc)
            return 1

    payload = result.to_dict()
    message = json.dumps(payload, ensure_ascii=False)
    if payload.get("error"):
        logger.warning("Approval completed with warnings: %s", payload["error"])
    logger.info("Approval result: %s", message)
    return 0
