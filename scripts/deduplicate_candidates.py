import asyncio
import logging
from collections import defaultdict

from sqlalchemy import delete, select

from app.db import SessionLocal, configure_engine
from app.models.gym_candidate import CandidateStatus, GymCandidate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def deduplicate_candidates():
    logger.info("Starting candidate deduplication...")

    async with SessionLocal() as session:
        # Fetch all candidates
        # We need name, address, id, tags, etc.
        stmt = select(GymCandidate).order_by(GymCandidate.id)
        result = await session.execute(stmt)
        all_candidates = result.scalars().all()

        # Group by Address + City (Simple fuzzy match)
        # Note: address_raw might be "1-2-3" or "1-2-3, Some City".
        # Ideally rely on strict address if available.
        # Fallback to name if address is empty? No, dupes common.
        # Let's rely on address.

        groups = defaultdict(list)
        norm_groups = defaultdict(list)

        for cand in all_candidates:
            if cand.status == CandidateStatus.approved:
                continue  # Don't touch approved ones

            # Key 1: Normalized Address (Strongest)
            parsed = cand.parsed_json or {}
            norm_addr = parsed.get("address")

            if norm_addr:
                norm_groups[norm_addr].append(cand)
            elif cand.address_raw:
                # Key 2: Raw Address (Cleanup spaces)
                clean_addr = cand.address_raw.replace(" ", "").replace("　", "")
                groups[clean_addr].append(cand)

        # Process duplicates
        duplicates_to_remove = set()

        def process_group(group_cands):
            if len(group_cands) < 2:
                return

            # Sort by quality:
            # 1. Has Tags (len)
            # 2. Name Length (longer is usually better/less generic?)
            # 3. ID (keep newer)

            def score(c):
                tags = (c.parsed_json or {}).get("tags", [])
                return (len(tags), len(c.name_raw), c.id)

            sorted_cands = sorted(group_cands, key=score, reverse=True)
            winner = sorted_cands[0]
            losers = sorted_cands[1:]

            logger.info(f"Dedupe ({len(group_cands)}): Keep {winner.id} ({winner.name_raw})")
            for loser in losers:
                logger.info(f"  -> Delete: {loser.id} ({loser.name_raw})")
                duplicates_to_remove.add(loser.id)

        for addr, cands in norm_groups.items():
            process_group(cands)

        for addr, cands in groups.items():
            # candidates in duplicates_to_remove might appear here too if logic overlaps?
            # Filter out already removed
            valid_cands = [c for c in cands if c.id not in duplicates_to_remove]
            process_group(valid_cands)

        if not duplicates_to_remove:
            logger.info("No duplicates found.")
            return

        logger.info(f"Deleting {len(duplicates_to_remove)} duplicate candidates...")

        # Batch delete
        # Chunking if too many
        ids = list(duplicates_to_remove)
        chunk_size = 100
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i : i + chunk_size]
            del_stmt = delete(GymCandidate).where(GymCandidate.id.in_(chunk))
            await session.execute(del_stmt)

        await session.commit()
        logger.info("Deduplication complete.")


if __name__ == "__main__":
    configure_engine()
    asyncio.run(deduplicate_candidates())
