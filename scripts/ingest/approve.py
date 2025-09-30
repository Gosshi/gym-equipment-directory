"""Dummy approval command for gym candidates."""

from __future__ import annotations

import json
import logging

from app.db import SessionLocal
from app.models.gym_candidate import GymCandidate

logger = logging.getLogger(__name__)


async def approve_candidate(candidate_id: int, dry_run: bool) -> int:
    """Log candidate information as a placeholder for approval logic."""
    async with SessionLocal() as session:
        candidate = await session.get(GymCandidate, candidate_id)
        if candidate is None:
            logger.error("Candidate %s not found", candidate_id)
            return 1

        payload = json.dumps(candidate.parsed_json or {}, ensure_ascii=False)
        logger.info(
            "Candidate %s summary: name='%s', pref='%s', city='%s', payload=%s",
            candidate.id,
            candidate.name_raw,
            candidate.pref_slug,
            candidate.city_slug,
            payload,
        )
        if dry_run:
            logger.info("Dry-run mode: no approval action taken")
        else:
            logger.info("TODO: implement approval logic (gyms/gym_equipments upsert)")
    return 0
