import asyncio
import logging
import re
import unicodedata
import uuid
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionLocal, configure_engine
from app.models.gym import Gym
from app.models.gym_candidate import CandidateStatus, GymCandidate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize_address(text: str | None) -> str:
    """Normalize Japanese address for fuzzy matching."""
    if not text:
        return ""

    # NFKC Normalization (Full-width to Half-width)
    normalized = unicodedata.normalize("NFKC", text)

    # Remove whitespace
    normalized = normalized.replace(" ", "").replace("　", "")

    # Kanji numbers to standard numbers (Simplified)
    # Mapping common ones found in addresses
    kanji_map = str.maketrans("一二三四五六七八九〇", "1234567890")
    normalized = normalized.translate(kanji_map)

    # Standardize separators
    # Convert '丁目', '番', '号', '番地' to '-'
    normalized = re.sub(r"丁目|番地|番|号", "-", normalized)

    # Remove trailing hyphens
    normalized = normalized.strip("-")

    return normalized


def is_name_similar(name1: str, name2: str, threshold: float = 0.8) -> bool:
    """Check if two facility names are similar."""
    if not name1 or not name2:
        return False

    # Normalize names
    n1 = unicodedata.normalize("NFKC", name1).replace(" ", "")
    n2 = unicodedata.normalize("NFKC", name2).replace(" ", "")

    # Check containment (High confidence if one is substring of another for long names)
    if len(n1) > 5 and n1 in n2:
        return True
    if len(n2) > 5 and n2 in n1:
        return True

    ratio = SequenceMatcher(None, n1, n2).ratio()
    return ratio >= threshold


async def auto_approve_candidates():
    logger.info("Starting auto-approval of new candidates...")

    async with SessionLocal() as session:
        # 1. Fetch all 'new' candidates with source_page loaded
        stmt = (
            select(GymCandidate)
            .where(GymCandidate.status == CandidateStatus.new)
            .options(selectinload(GymCandidate.source_page))
            .order_by(GymCandidate.id)
        )
        result = await session.execute(stmt)
        candidates = result.scalars().all()

        logger.info(f"Found {len(candidates)} new candidates.")

        # 2. Fetch all existing Gyms for comparison (Cache in memory if not too large)
        # Assuming < 1000 items, safe to load.
        stmt_gyms = select(Gym)
        result_gyms = await session.execute(stmt_gyms)
        existing_gyms = result_gyms.scalars().all()

        # Pre-process existing gyms for faster lookup
        gyms_by_url = {g.official_url: g for g in existing_gyms if g.official_url}
        gyms_by_city = {}
        for g in existing_gyms:
            if g.city:
                if g.city not in gyms_by_city:
                    gyms_by_city[g.city] = []
                gyms_by_city[g.city].append(g)

        approved_count = 0
        merged_count = 0

        for cand in candidates:
            # Skip if critical info missing
            if not cand.name_raw:
                continue

            parsed = cand.parsed_json or {}
            cand_url = cand.source_page.url if cand.source_page else None
            cand_city = cand.city_slug

            # --- MATCHING LOGIC ---
            matched_gym: Gym | None = None

            # 1. Match by URL (Exact)
            if cand_url and cand_url in gyms_by_url:
                matched_gym = gyms_by_url[cand_url]
                logger.info(f"Match found by URL: {cand.name_raw} -> {matched_gym.name}")

            # 2. Match by Address (Normalized)
            if not matched_gym and cand.address_raw:
                c_norm_addr = normalize_address(cand.address_raw)
                if c_norm_addr:
                    for g in existing_gyms:
                        if g.address and normalize_address(g.address) == c_norm_addr:
                            matched_gym = g
                            logger.info(f"Match found by Address: {cand.name_raw} -> {g.name}")
                            break

            # 3. Match by Name Similarity (Same City)
            if not matched_gym and cand_city and cand_city in gyms_by_city:
                for g in gyms_by_city[cand_city]:
                    if is_name_similar(cand.name_raw, g.name):
                        matched_gym = g
                        logger.info(f"Match found by Name Similarity: {cand.name_raw} -> {g.name}")
                        break

            # --- ACTION ---

            if matched_gym:
                # MERGE TAGS
                current_tags = set((matched_gym.parsed_json or {}).get("tags", []))
                new_tags = set(parsed.get("tags", []))

                if not new_tags.issubset(current_tags):
                    merged_tags = list(current_tags | new_tags)
                    # Update Gym
                    g_parsed = dict(matched_gym.parsed_json) if matched_gym.parsed_json else {}
                    g_parsed["tags"] = merged_tags
                    matched_gym.parsed_json = g_parsed
                    logger.info(f"  -> Merged tags: {new_tags - current_tags}")

                # Update Candidate Status
                # Mark as ignored (because it's merged/duplicate)
                cand.status = CandidateStatus.ignored
                merged_count += 1

            else:
                # CREATE NEW GYM?
                # Condition: High Confidence
                # 1. Source is municipal (implicitly true if trusted)
                # 2. LLM says is_gym=True
                # 3. Has Address

                # Check parsed_json 'is_gym'
                is_gym = parsed.get("is_gym")

                if is_gym and cand.address_raw:
                    # Create New Gym
                    logger.info(f"Creating NEW Gym: {cand.name_raw}")

                    new_slug = f"gym-{uuid.uuid4().hex[:8]}"

                    new_gym = Gym(
                        name=cand.name_raw,
                        address=cand.address_raw,
                        pref=cand.pref_slug,  # assuming these match
                        city=cand.city_slug,
                        official_url=cand_url,
                        latitude=cand.latitude,
                        longitude=cand.longitude,
                        parsed_json=parsed,
                        slug=new_slug,
                        canonical_id=uuid.uuid4(),
                        created_at=cand.created_at,  # inherit
                    )
                    session.add(new_gym)
                    await session.flush()  # to get ID

                    cand.status = CandidateStatus.approved
                    approved_count += 1
                else:
                    # Leave as 'new' for manual review
                    pass

        await session.commit()
        logger.info(
            f"Auto-approval complete. Merged: {merged_count}, Approved (New): {approved_count}"
        )


if __name__ == "__main__":
    configure_engine()
    asyncio.run(auto_approve_candidates())
