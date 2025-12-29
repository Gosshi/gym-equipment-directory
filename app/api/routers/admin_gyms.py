"""Admin routes for gym management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_session
from app.models import Gym
from app.services.scrape_utils import try_scrape_official_url

router = APIRouter(prefix="/admin/gyms", tags=["admin"])


class ScrapeOfficialUrlRequest(BaseModel):
    """Request to scrape an official URL for an existing gym."""

    official_url: str


class ScrapeOfficialUrlResponse(BaseModel):
    """Response from scraping an official URL."""

    gym_id: int
    official_url: str
    scraped: bool
    message: str


@router.post("/{gym_id}/scrape-official-url", response_model=ScrapeOfficialUrlResponse)
async def scrape_official_url(
    gym_id: int,
    payload: ScrapeOfficialUrlRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Scrape an official URL for an existing gym and merge data into parsed_json.

    This endpoint allows updating the official_url for approved gyms and triggering
    a scrape to extract additional information.
    """
    gym = await session.get(Gym, gym_id)
    if not gym:
        raise HTTPException(status_code=404, detail="gym not found")

    official_url = payload.official_url.strip()
    if not official_url:
        raise HTTPException(status_code=400, detail="official_url is required")

    # Try to scrape the official URL
    merged_json = await try_scrape_official_url(
        official_url,
        gym.official_url,  # existing official_url for comparison
        gym.parsed_json,
    )

    if merged_json is None:
        # Scraping failed or was skipped, but still update the official_url
        gym.official_url = official_url
        await session.commit()
        return ScrapeOfficialUrlResponse(
            gym_id=gym_id,
            official_url=official_url,
            scraped=False,
            message="URL updated but scraping skipped (same URL or robots.txt blocked)",
        )

    # Scraping succeeded, update both parsed_json and official_url
    gym.parsed_json = merged_json
    gym.official_url = official_url
    await session.commit()

    return ScrapeOfficialUrlResponse(
        gym_id=gym_id,
        official_url=official_url,
        scraped=True,
        message="Official URL scraped successfully and merged into gym data",
    )


class UpdateOfficialUrlRequest(BaseModel):
    """Request to update official URL without scraping."""

    official_url: str | None


class GymBasicInfo(BaseModel):
    """Basic gym info for admin responses."""

    id: int
    slug: str
    name: str
    official_url: str | None


@router.patch("/{gym_id}/official-url", response_model=GymBasicInfo)
async def update_official_url(
    gym_id: int,
    payload: UpdateOfficialUrlRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Update the official URL for a gym without scraping."""
    gym = await session.get(Gym, gym_id)
    if not gym:
        raise HTTPException(status_code=404, detail="gym not found")

    gym.official_url = payload.official_url
    await session.commit()

    return GymBasicInfo(
        id=int(gym.id),
        slug=gym.slug,
        name=gym.name,
        official_url=gym.official_url,
    )
