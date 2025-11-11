"""Run the municipal ingest pipeline end-to-end for selected areas."""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models.gym_candidate import CandidateStatus, GymCandidate
from app.models.scraped_page import ScrapedPage
from app.models.source import Source
from app.schemas.admin_candidates import ApproveRequest
from app.services.candidates import CandidateServiceError, approve_candidate
from scripts.ingest.fetch_http import (
    DEFAULT_MAX_DELAY,
    DEFAULT_MIN_DELAY,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    fetch_http_pages,
)
from scripts.ingest.normalize import normalize_candidates
from scripts.ingest.parse import parse_pages
from scripts.ingest.sources_registry import SOURCES, MunicipalSource
from scripts.tools.geocode_missing import geocode_missing_records
from scripts.update_freshness import main as update_freshness_main

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AreaTarget:
    """Resolved ingest configuration for a municipal area."""

    pref: str
    city: str
    source_id: str
    descriptor: MunicipalSource


def _parse_area_tokens(raw: Sequence[str]) -> list[str]:
    tokens: list[str] = []
    for item in raw:
        if not item:
            continue
        parts = [part.strip() for part in item.split(",") if part.strip()]
        tokens.extend(parts)
    return tokens


def _resolve_area(token: str) -> AreaTarget:
    if ":" not in token:
        msg = f"Area token must be pref:city format, got '{token}'"
        raise ValueError(msg)
    pref, city = (segment.strip().lower() for segment in token.split(":", 1))
    for source_id, descriptor in SOURCES.items():
        if descriptor.pref_slug == pref and descriptor.city_slug == city:
            return AreaTarget(pref=pref, city=city, source_id=source_id, descriptor=descriptor)
    msg = f"Unsupported municipal area: pref={pref}, city={city}"
    raise ValueError(msg)


def _should_auto_approve(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return False
    return bool(meta.get("create_gym"))


async def _fetch_pending_create_gym_candidates(
    session: AsyncSession, area: AreaTarget
) -> list[int]:
    stmt: Select[tuple[int, dict[str, Any] | None]] = (
        select(GymCandidate.id, GymCandidate.parsed_json)
        .join(ScrapedPage, GymCandidate.source_page_id == ScrapedPage.id)
        .join(Source, ScrapedPage.source_id == Source.id)
        .where(Source.title == area.source_id)
        .where(GymCandidate.status == CandidateStatus.new)
        .order_by(GymCandidate.id.asc())
    )
    result = await session.execute(stmt)
    targets: list[int] = []
    for candidate_id, parsed in result.all():
        if _should_auto_approve(parsed):
            targets.append(int(candidate_id))
    return targets


async def _approve_candidates(area: AreaTarget) -> int:
    async with SessionLocal() as session:
        candidate_ids = await _fetch_pending_create_gym_candidates(session, area)
        if not candidate_ids:
            logger.info("No pending create_gym candidates for %s", area.source_id)
            return 0

        approved = 0
        request = ApproveRequest()
        for candidate_id in candidate_ids:
            try:
                await approve_candidate(session, candidate_id, request)
            except CandidateServiceError as exc:
                msg = f"Approval failed for candidate {candidate_id} ({area.source_id})"
                raise RuntimeError(msg) from exc
            approved += 1
            logger.info("Approved candidate %s for %s", candidate_id, area.source_id)

        remaining = await _fetch_pending_create_gym_candidates(session, area)
        if remaining:
            msg = (
                "Pending create_gym candidates remain after approval: "
                f"{remaining} for {area.source_id}"
            )
            raise RuntimeError(msg)
        return approved


async def _run_area(area: AreaTarget, limit: int | None) -> None:
    logger.info(
        "Sync start for %s:%s (source=%s, limit=%s)",
        area.pref,
        area.city,
        area.source_id,
        limit if limit is not None else "auto",
    )
    await fetch_http_pages(
        area.source_id,
        pref=area.pref,
        city=area.city,
        limit=limit,
        min_delay=DEFAULT_MIN_DELAY,
        max_delay=DEFAULT_MAX_DELAY,
        respect_robots=True,
        user_agent=DEFAULT_USER_AGENT,
        timeout=DEFAULT_TIMEOUT,
        dry_run=False,
        force=False,
    )
    await parse_pages(area.source_id, limit)
    await normalize_candidates(area.source_id, limit, geocode_missing=False)
    approved = await _approve_candidates(area)
    logger.info("Approved %s candidates for %s", approved, area.source_id)


async def _run_pipeline(areas: Sequence[str], limit: int | None) -> None:
    tokens = _parse_area_tokens(areas)
    if not tokens:
        raise ValueError("At least one area must be provided")
    targets = [_resolve_area(token) for token in tokens]

    for target in targets:
        await _run_area(target, limit)

    await geocode_missing_records("gyms", limit=limit, origin="scraped")
    await geocode_missing_records("candidates", limit=limit)
    await update_freshness_main()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run municipal ingest pipeline end-to-end"
    )
    parser.add_argument(
        "--areas",
        nargs="+",
        required=True,
        help="Municipal areas in pref:city format. Comma separated values are allowed.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Optional limit applied to fetch, parse, normalize, and geocode steps. "
            "Defaults to pipeline-specific behavior when omitted."
        ),
    )
    return parser


async def _async_main(args: argparse.Namespace) -> int:
    limit = args.limit
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    await _run_pipeline(args.areas, limit)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return asyncio.run(_async_main(args))
    except Exception:  # pragma: no cover - CLI safeguard
        logger.exception("Municipal sync failed")
        return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
