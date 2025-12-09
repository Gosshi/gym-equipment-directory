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
        # Fetch lightweight tuples instead of full objects
        stmt = select(
            GymCandidate.id,
            GymCandidate.name_raw,
            GymCandidate.address_raw,
            GymCandidate.parsed_json,
            GymCandidate.status,
        ).order_by(GymCandidate.id)

        # Use stream with yield_per just to be safe during fetch even if we collect list
        # Actually for grouping we probably need them all.
        # But constructing tuples is cheaper than ORM instances.
        result = await session.execute(stmt)
        all_candidates = result.all()  # List of Row objects (tuples)

        # Group by Address + City
        groups = defaultdict(list)
        norm_groups = defaultdict(list)

        for row in all_candidates:
            cid, cname, caddr, cparsed, cstatus = row

            if cstatus == CandidateStatus.approved:
                continue

            # Key 1: Normalized Address (Strongest)
            parsed = cparsed or {}
            norm_addr = parsed.get("address")

            if norm_addr:
                norm_groups[norm_addr].append(row)
            elif caddr:
                # Key 2: Raw Address
                clean_addr = caddr.replace(" ", "").replace("　", "")
                groups[clean_addr].append(row)

        # Process duplicates
        duplicates_to_remove = set()

        def process_group(group_cands):
            if len(group_cands) < 2:
                return

            # Sort by quality:
            # 1. Has Tags (len)
            # 2. Name Length (longer is usually better/less generic?)
            # 3. ID (keep newer)

            def score(row):
                cid, cname, caddr, cparsed, cstatus = row
                tags = (cparsed or {}).get("tags", [])
                return (len(tags), len(cname or ""), cid)

            sorted_rows = sorted(group_cands, key=score, reverse=True)
            winner = sorted_rows[0]
            losers = sorted_rows[1:]

            w_id, w_name, _, _, _ = winner

            logger.info(f"Dedupe ({len(group_cands)}): Keep {w_id} ({w_name})")
            for loser in losers:
                l_id, l_name, _, _, _ = loser
                logger.info(f"  -> Delete: {l_id} ({l_name})")
                duplicates_to_remove.add(l_id)

        for addr, cands in norm_groups.items():
            process_group(cands)

        for addr, cands in groups.items():
            # candidates in duplicates_to_remove might appear here too if logic overlaps?
            # Filter out already removed
            valid_cands = [row for row in cands if row[0] not in duplicates_to_remove]
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
