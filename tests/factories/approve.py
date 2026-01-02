from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CandidateStatus,
    Equipment,
    Gym,
    GymCandidate,
    ScrapedPage,
    Source,
    SourceType,
)


async def create_equipment(
    session: AsyncSession,
    *,
    slug: str,
    name: str = "Test Equipment",
    category: str = "machine",
) -> Equipment:
    equipment = Equipment(slug=slug, name=name, category=category)
    session.add(equipment)
    await session.flush()
    return equipment


async def create_source(session: AsyncSession, title: str) -> Source:
    source = Source(source_type=SourceType.official_site, title=title, url="https://example.com")
    session.add(source)
    await session.flush()
    return source


async def create_page(session: AsyncSession, source_id: int, slug: str) -> ScrapedPage:
    page = ScrapedPage(
        source_id=source_id,
        url=f"https://example.com/{slug}",
        fetched_at=datetime.now(UTC),
        http_status=200,
    )
    session.add(page)
    await session.flush()
    return page


async def create_gym(
    session: AsyncSession,
    *,
    name: str,
    slug: str,
    official_url: str | None = None,
    address: str | None = None,
    pref: str = "tokyo",
    city: str = "koto",
) -> Gym:
    """Create a Gym record for testing."""
    gym = Gym(
        name=name,
        slug=slug,
        official_url=official_url,
        address=address,
        pref=pref,
        city=city,
        latitude=35.6,
        longitude=139.8,
    )
    session.add(gym)
    await session.flush()
    return gym


async def create_candidate(
    session: AsyncSession,
    *,
    name: str,
    page: ScrapedPage,
    parsed_json: dict,
    status: CandidateStatus = CandidateStatus.new,
    address_raw: str | None = None,
) -> GymCandidate:
    candidate = GymCandidate(
        source_page_id=page.id,
        name_raw=name,
        address_raw=address_raw or parsed_json.get("address", "東京都江東区東砂4-24-1"),
        pref_slug="tokyo",
        city_slug="koto",
        latitude=35.6,
        longitude=139.8,
        parsed_json=parsed_json,
        status=status,
    )
    session.add(candidate)
    await session.flush()
    await session.commit()
    return candidate


__all__ = [
    "create_equipment",
    "create_gym",
    "create_source",
    "create_page",
    "create_candidate",
]
