import asyncio
import logging
import os

from sqlalchemy import case, func, select

from app.db import SessionLocal, configure_engine
from app.models.gym_candidate import CandidateStatus, GymCandidate
from app.models.scraped_page import ScrapedPage
from app.models.source import Source

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def analyze_stats():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL not set")
        return
    configure_engine(dsn)

    async with SessionLocal() as session:
        # Query stats per source
        # We want: Source Title, Total Pages, Last Fetch, Total Candidates, New, Approved, Rejected

        stmt = (
            select(
                Source.title,
                func.count(ScrapedPage.id).label("total_pages"),
                func.max(ScrapedPage.fetched_at).label("last_fetch"),
                func.count(GymCandidate.id).label("total_candidates"),
                func.count(case((GymCandidate.status == CandidateStatus.new, 1))).label(
                    "new_candidates"
                ),
                func.count(case((GymCandidate.status == CandidateStatus.approved, 1))).label(
                    "approved_candidates"
                ),
                func.count(case((GymCandidate.status == CandidateStatus.rejected, 1))).label(
                    "rejected_candidates"
                ),
            )
            .join(ScrapedPage, Source.id == ScrapedPage.source_id)
            .outerjoin(GymCandidate, ScrapedPage.id == GymCandidate.source_page_id)
            .group_by(Source.id, Source.title)
            .order_by(Source.title)
        )

        result = await session.execute(stmt)
        rows = result.all()

        if not rows:
            logger.info("No data found.")
            return

        # Header
        headers = ["Source", "Pages", "Last Fetch", "Candidates", "New", "Approved", "Rejected"]
        widths = [30, 8, 20, 12, 8, 10, 10]

        header_row = "".join(f"{h:<{w}}" for h, w in zip(headers, widths))
        logger.info("-" * len(header_row))
        logger.info(header_row)
        logger.info("-" * len(header_row))

        total_pages = 0
        total_cands = 0

        for row in rows:
            title = row.title or "Unknown"
            last_fetch = row.last_fetch.strftime("%Y-%m-%d %H:%M") if row.last_fetch else "-"

            logger.info(
                f"{title[:28]:<30}"
                f"{row.total_pages:<8}"
                f"{last_fetch:<20}"
                f"{row.total_candidates:<12}"
                f"{row.new_candidates:<8}"
                f"{row.approved_candidates:<10}"
                f"{row.rejected_candidates:<10}"
            )

            total_pages += row.total_pages
            total_cands += row.total_candidates

        logger.info("-" * len(header_row))
        logger.info(f"Total Pages: {total_pages}, Total Candidates: {total_cands}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    asyncio.run(analyze_stats())
