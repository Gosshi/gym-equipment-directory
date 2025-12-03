import asyncio
import os
import sys
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add project root to python path
sys.path.append(os.getcwd())

from app.models.gym import Gym
from app.models.gym_candidate import CandidateStatus, GymCandidate
from app.models.scraped_page import ScrapedPage
from app.models.source import Source, SourceType
from scripts.ingest.diff import classify_candidates

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL is not set")
    sys.exit(1)


async def main():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        print("Setting up test data...")

        # Create a Source
        source = Source(
            title="test_source", url="http://example.com", source_type=SourceType.official_site
        )
        session.add(source)
        await session.flush()

        # Create an existing Gym
        existing_gym = Gym(
            name="Existing Gym",
            slug=f"existing-gym-{uuid.uuid4()}",
            canonical_id=str(uuid.uuid4()),
            official_url="http://example.com/gym1",
            address="Tokyo, Chiyoda, 1-1-1",
            pref="Tokyo",
            city="Chiyoda",
        )
        session.add(existing_gym)
        await session.flush()

        # Case 1: Duplicate by URL
        page1 = ScrapedPage(
            source_id=source.id,
            url="http://example.com/gym1",  # Same URL as existing_gym
            fetched_at=datetime.now(),
            content_hash="hash1",
        )
        session.add(page1)
        await session.flush()

        cand1 = GymCandidate(
            source_page_id=page1.id,
            name_raw="Different Name",
            address_raw="Different Address",
            status=CandidateStatus.new,
        )
        session.add(cand1)
        await session.flush()

        # Case 2: Duplicate by Address + Name
        page2 = ScrapedPage(
            source_id=source.id,
            url="http://example.com/gym2",  # Different URL
            fetched_at=datetime.now(),
            content_hash="hash2",
        )
        session.add(page2)
        await session.flush()

        cand2 = GymCandidate(
            source_page_id=page2.id,
            name_raw="Existing Gym",  # Same Name
            address_raw="Tokyo, Chiyoda, 1-1-1",  # Same Address
            status=CandidateStatus.new,
        )
        session.add(cand2)
        await session.flush()

        # Case 3: New (Different URL, Different Address)
        page3 = ScrapedPage(
            source_id=source.id,
            url="http://example.com/gym3",
            fetched_at=datetime.now(),
            content_hash="hash3",
        )
        session.add(page3)
        await session.flush()

        cand3 = GymCandidate(
            source_page_id=page3.id,
            name_raw="New Gym",
            address_raw="Tokyo, Shinjuku, 2-2-2",
            status=CandidateStatus.new,
        )
        session.add(cand3)
        await session.flush()

        print(
            f"Created candidates: {cand1.id} (URL Dup), "
            f"{cand2.id} (Addr+Name Dup), {cand3.id} (New)"
        )

        # Run classification
        print("Running classification...")
        summary = await classify_candidates(
            session, source="test_source", candidate_ids=[cand1.id, cand2.id, cand3.id]
        )

        print(f"Result: {summary}")

        # Verify
        assert cand1.id in summary.duplicate_ids, "Case 1 should be duplicate (URL)"
        assert cand2.id in summary.duplicate_ids, "Case 2 should be duplicate (Addr+Name)"
        assert cand3.id in summary.new_ids, "Case 3 should be new"

        print("Verification PASSED!")

        # Verify DB state
        await session.refresh(cand1)
        await session.refresh(cand2)
        await session.refresh(cand3)

        print(f"Cand1 status: {cand1.status}")
        print(f"Cand2 status: {cand2.status}")
        print(f"Cand3 status: {cand3.status}")

        await session.delete(cand1)
        await session.delete(cand2)
        await session.delete(cand3)
        await session.delete(page1)
        await session.delete(page2)
        await session.delete(page3)
        await session.delete(existing_gym)
        await session.delete(source)
        await session.commit()
        print("Cleanup done.")


if __name__ == "__main__":
    asyncio.run(main())
