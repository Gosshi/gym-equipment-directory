from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Equipment, Gym, GymCandidate, GymEquipment
from app.models.gym_candidate import CandidateStatus
from app.models.gym_equipment import Availability, VerificationStatus
from app.services.canonical import make_canonical_id

logger = logging.getLogger(__name__)


class ApprovalError(RuntimeError):
    """Base error for approval failures."""


class CandidateNotFoundError(ApprovalError):
    """Raised when the target candidate does not exist."""


class CandidateStatusConflictError(ApprovalError):
    """Raised when the candidate has already been processed."""


class InvalidCandidatePayloadError(ApprovalError):
    """Raised when required fields are missing from the candidate payload."""


@dataclass
class FieldChange:
    field: str
    before: Any
    after: Any


@dataclass
class GymPlan:
    action: str
    gym: Gym | None
    slug: str | None
    canonical_id: str | None
    create_kwargs: dict[str, Any] = field(default_factory=dict)
    update_fields: dict[str, Any] = field(default_factory=dict)
    changes: list[FieldChange] = field(default_factory=list)
    result: Gym | None = None

    async def apply(self, session: AsyncSession) -> Gym | None:
        if self.action == "skip":
            self.result = None
            return None
        if self.action == "create":
            payload = dict(self.create_kwargs)
            payload.setdefault("slug", self.slug)
            payload.setdefault("canonical_id", self.canonical_id)
            gym = Gym(**payload)
            session.add(gym)
            await session.flush()
            self.result = gym
            return gym
        if self.action in {"update", "reuse"}:
            gym = self.gym
            if gym is None:
                raise ApprovalError("cannot update gym: no target gym provided")
            for key, value in self.update_fields.items():
                setattr(gym, key, value)
            await session.flush()
            self.result = gym
            return gym
        raise ApprovalError(f"unsupported gym action: {self.action}")

    def to_dict(self, dry_run: bool) -> dict[str, Any]:
        gym_id: int | None
        slug: str | None
        if dry_run:
            gym_id = self.gym.id if self.gym and self.gym.id is not None else None
            slug = self.slug or (self.gym.slug if self.gym else None)
        else:
            gym_obj = self.result or self.gym
            gym_id = int(gym_obj.id) if gym_obj and gym_obj.id is not None else None
            slug = gym_obj.slug if gym_obj else self.slug
        data = {
            "action": self.action,
            "gym_id": gym_id,
            "slug": slug,
            "canonical_id": self.canonical_id if self.action == "create" else None,
            "changes": [
                {"field": c.field, "before": c.before, "after": c.after} for c in self.changes
            ],
        }
        if self.action == "create":
            data["after"] = self.create_kwargs
        if self.action == "update":
            data["after"] = {change.field: change.after for change in self.changes}
        return data


@dataclass
class EquipmentPlan:
    slug: str
    equipment: Equipment | None
    action: str
    count_before: int | None
    count_after: int | None
    existing: GymEquipment | None = None
    warnings: list[str] = field(default_factory=list)
    timestamp: datetime | None = None
    result: GymEquipment | None = None

    async def apply(self, session: AsyncSession, gym_id: int | None, timestamp: datetime) -> None:
        if self.action == "skip":
            return
        if self.equipment is None:
            logger.warning("Skipping equipment with unknown slug '%s'", self.slug)
            return
        if gym_id is None:
            raise ApprovalError("gym must be persisted before linking equipments")
        self.timestamp = timestamp
        if self.action == "insert":
            link = GymEquipment(
                gym_id=gym_id,
                equipment_id=self.equipment.id,
                availability=Availability.present,
                count=self.count_after,
                verification_status=VerificationStatus.user_verified,
                last_verified_at_cached=datetime.now(UTC),
            )
            session.add(link)
            await session.flush()
            self.result = link
            return
        if self.action == "merge":
            link = self.existing
            if link is None:
                # Unexpected state: treat as insert
                logger.warning("Merge requested but no existing record for slug '%s'", self.slug)
                self.action = "insert"
                await self.apply(session, gym_id, timestamp)
                return
            if self.count_after is not None and self.count_after != link.count:
                link.count = self.count_after
            link.last_verified_at = timestamp
            await session.flush()
            self.result = link
            return
        raise ApprovalError(f"unsupported equipment action: {self.action}")

    def to_dict(self, dry_run: bool) -> dict[str, Any]:
        equipment_id = None
        if self.equipment and self.equipment.id is not None:
            equipment_id = int(self.equipment.id)
        before = {"count": self.count_before}
        after = {"count": self.count_after}
        if not dry_run and self.result is not None:
            after = {"count": self.result.count}
        data = {
            "slug": self.slug,
            "equipment_id": equipment_id,
            "action": self.action,
            "before": before,
            "after": after,
            "warnings": list(self.warnings),
        }
        if not dry_run and self.result is not None and self.result.last_verified_at is not None:
            data["last_verified_at"] = self.result.last_verified_at.isoformat()
        elif dry_run:
            ts = self.timestamp or datetime.now(UTC)
            data["last_verified_at"] = ts.isoformat()
        return data


@dataclass
class ApprovalPlan:
    candidate: GymCandidate
    candidate_status: CandidateStatus
    gym_plan: GymPlan
    equipment_plans: list[EquipmentPlan]
    approved_gym_slug: str | None

    async def apply(self, session: AsyncSession) -> Gym | None:
        gym = await self.gym_plan.apply(session)
        if gym is None and self.candidate_status == CandidateStatus.approved:
            raise ApprovalError("approval plan requires a gym")
        gym_id = int(gym.id) if gym and gym.id is not None else None
        timestamp = datetime.now(UTC)
        for plan in self.equipment_plans:
            await plan.apply(session, gym_id, timestamp)
        return gym


@dataclass
class ApproveResponse:
    candidate_id: int
    dry_run: bool
    gym: GymPlan
    equipments: list[EquipmentPlan]
    candidate_status: CandidateStatus
    approved_gym_slug: str | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "candidate_id": self.candidate_id,
            "dry_run": self.dry_run,
            "gym": self.gym.to_dict(self.dry_run),
            "equipments": [plan.to_dict(self.dry_run) for plan in self.equipments],
            "candidate": {
                "status": self.candidate_status.value,
                "approved_gym_slug": self.approved_gym_slug,
            },
        }
        if self.error:
            payload["error"] = self.error
        return payload


_ARTICLE_PAT = re.compile(
    r"/introduction/(?:post_|tr_detail\.html|trainingmachine\.html|notes\.html)$"
)
_INTRO_BASE_PAT = re.compile(r"(/sports_center\d+/introduction)/?")
_CENTER_NO_PAT = re.compile(r"/sports_center(\d+)/")


def _sanitize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        text = str(value)
    text = unicodedata.normalize("NFKC", text)
    return text.strip()


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    cleaned = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff\u3040-\u30ff\s-]", "", normalized)
    lowered = cleaned.lower()
    tokens = re.split(r"[\s_-]+", lowered)
    slug = "-".join(filter(None, tokens))
    return slug[:64].strip("-")


def _should_use_address_in_slug(address: str) -> bool:
    if len(address) > 40:
        return False
    if ">>>" in address:
        return False
    if re.search(r"[。、「」、.!?]", address):
        return False
    return True


def _build_slug(name: str, address: str | None, city: str | None, pref: str | None) -> str:
    parts = [name]
    if city:
        parts.append(city)
    if pref:
        parts.append(pref)
    if address:
        cleaned_address = re.sub(r"\b\d{3}-\d{4}\b", "", address).strip()
        if cleaned_address and _should_use_address_in_slug(cleaned_address):
            parts.append(cleaned_address)
    slug = _slugify("-".join(parts))
    if not slug:
        msg = f"failed to generate slug from name='{name}'"
        raise InvalidCandidatePayloadError(msg)
    return slug


def _parse_center_no(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        digits = re.sub(r"\D", "", value)
        if digits:
            try:
                return int(digits)
            except ValueError:  # pragma: no cover - defensive
                return None
    return None


def _extract_center_no(url: str | None) -> int | None:
    if not url:
        return None
    match = _CENTER_NO_PAT.search(url)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:  # pragma: no cover - defensive
        return None


def _to_intro_base_url(url: str | None) -> str | None:
    if not url:
        return None
    match = _INTRO_BASE_PAT.search(url)
    if not match:
        return None
    end = match.end(1)
    return f"{url[:end]}/"


def _normalize_official_url(page_url: str | None) -> str | None:
    if not page_url:
        return None
    base = _to_intro_base_url(page_url)
    if base:
        return base
    return page_url


class ApproveService:
    """Service responsible for approving normalized gym candidates."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def approve(self, candidate_id: int, *, dry_run: bool = False) -> ApproveResponse:
        txn = await self._session.begin()
        candidate = await self._load_candidate(candidate_id)
        if candidate is None:
            await txn.rollback()
            logger.warning("Candidate %s not found", candidate_id)
            raise CandidateNotFoundError(f"candidate {candidate_id} not found")
        if candidate.status is not CandidateStatus.new:
            await txn.rollback()
            logger.warning("Candidate %s status conflict: %s", candidate_id, candidate.status)
            raise CandidateStatusConflictError(
                f"candidate {candidate_id} status is {candidate.status}"
            )
        try:
            plan = await self._build_plan(candidate)
        except ApprovalError as exc:
            await txn.rollback()
            logger.warning("Failed to build approval plan for candidate %s: %s", candidate_id, exc)
            if dry_run:
                response = ApproveResponse(
                    candidate_id=int(candidate.id),
                    dry_run=True,
                    gym=GymPlan(action="skip", gym=None, slug=None, canonical_id=None),
                    equipments=[],
                    candidate_status=candidate.status,
                    approved_gym_slug=None,
                    error=str(exc),
                )
                return response
            raise
        if dry_run:
            await txn.rollback()
            logger.info(
                "Approval dry-run candidate=%s action=%s target_slug=%s",
                candidate_id,
                plan.gym_plan.action,
                plan.gym_plan.slug,
            )
            return ApproveResponse(
                candidate_id=int(candidate.id),
                dry_run=True,
                gym=plan.gym_plan,
                equipments=plan.equipment_plans,
                candidate_status=plan.candidate_status,
                approved_gym_slug=plan.approved_gym_slug,
            )
        try:
            gym = await plan.apply(self._session)
            candidate.status = plan.candidate_status
            if plan.candidate_status is CandidateStatus.approved and gym:
                plan.approved_gym_slug = gym.slug
            await self._session.flush()
            await txn.commit()
        except Exception:
            await txn.rollback()
            logger.exception("Approval failed for candidate %s", candidate_id)
            raise
        gym_id = int(gym.id) if gym and gym.id is not None else None
        logger.info(
            "Approval succeeded candidate=%s gym_id=%s action=%s",
            candidate_id,
            gym_id,
            plan.gym_plan.action,
        )
        return ApproveResponse(
            candidate_id=int(candidate.id),
            dry_run=False,
            gym=plan.gym_plan,
            equipments=plan.equipment_plans,
            candidate_status=plan.candidate_status,
            approved_gym_slug=plan.approved_gym_slug,
        )

    async def _load_candidate(self, candidate_id: int) -> GymCandidate | None:
        stmt: Select[GymCandidate] = (
            select(GymCandidate).where(GymCandidate.id == candidate_id).with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _build_plan(self, candidate: GymCandidate) -> ApprovalPlan:
        parsed = candidate.parsed_json if isinstance(candidate.parsed_json, dict) else {}
        meta = parsed.get("meta") if isinstance(parsed.get("meta"), dict) else {}
        create_gym = bool(meta.get("create_gym", True))
        if not create_gym:
            gym_plan = GymPlan(action="skip", gym=None, slug=None, canonical_id=None)
            return ApprovalPlan(
                candidate=candidate,
                candidate_status=CandidateStatus.ignored,
                gym_plan=gym_plan,
                equipment_plans=[],
                approved_gym_slug=None,
            )

        name = _sanitize_text(parsed.get("facility_name")) or _sanitize_text(candidate.name_raw)
        if not name:
            raise InvalidCandidatePayloadError("facility name is required")
        pref = _sanitize_text(candidate.pref_slug)
        city = _sanitize_text(candidate.city_slug)
        address = _sanitize_text(parsed.get("address")) or _sanitize_text(candidate.address_raw)
        page_url = _sanitize_text(parsed.get("page_url"))
        center_no = _parse_center_no(parsed.get("center_no"))
        if center_no is None:
            center_no = _extract_center_no(page_url)
        target_slug = _sanitize_text(meta.get("target_gym_slug"))

        target_gym: Gym | None = None
        if target_slug:
            target_gym = await self._find_gym_by_slug(target_slug)
        if target_gym is None and center_no is not None:
            target_gym = await self._find_gym_by_center_no(center_no)
        if target_gym is None and page_url:
            official = _normalize_official_url(page_url)
            if official:
                target_gym = await self._find_gym_by_official_url(official)

        canonical_id = make_canonical_id(pref, city, name)
        official_url = _normalize_official_url(page_url)
        gym_plan = await self._build_gym_plan(
            candidate,
            target_gym,
            name=name,
            pref=pref,
            city=city,
            address=address or None,
            canonical_id=canonical_id,
            official_url=official_url,
        )

        equipment_plans = await self._build_equipment_plans(
            parsed.get("equipments_slotted"),
            target_gym,
        )

        approved_gym_slug = target_gym.slug if target_gym else gym_plan.slug
        return ApprovalPlan(
            candidate=candidate,
            candidate_status=CandidateStatus.approved,
            gym_plan=gym_plan,
            equipment_plans=equipment_plans,
            approved_gym_slug=approved_gym_slug,
        )

    async def _build_gym_plan(
        self,
        candidate: GymCandidate,
        target_gym: Gym | None,
        *,
        name: str,
        pref: str,
        city: str,
        address: str | None,
        canonical_id: str,
        official_url: str | None,
    ) -> GymPlan:
        if not pref or not city:
            raise InvalidCandidatePayloadError("pref_slug and city_slug are required")
        existing = await self._find_gym_by_canonical_id(canonical_id)
        if target_gym is None and existing is not None:
            target_gym = existing
        if target_gym:
            updates: dict[str, Any] = {}
            changes: list[FieldChange] = []
            for attr, value in (
                ("name", name),
                ("address", address),
                ("pref", pref),
                ("city", city),
            ):
                current = getattr(target_gym, attr, None)
                if current:
                    continue
                if value:
                    updates[attr] = value
                    changes.append(FieldChange(field=attr, before=current, after=value))
            if official_url and not getattr(target_gym, "official_url", None):
                updates["official_url"] = official_url
                changes.append(FieldChange(field="official_url", before=None, after=official_url))
            action = "update" if updates else "reuse"
            return GymPlan(
                action=action,
                gym=target_gym,
                slug=target_gym.slug,
                canonical_id=None,
                update_fields=updates,
                changes=changes,
            )

        slug_base = _build_slug(name, address, city, pref)
        slug = await self._generate_unique_slug(slug_base)
        create_kwargs: dict[str, Any] = {
            "slug": slug,
            "canonical_id": canonical_id,
            "name": name,
            "pref": pref,
            "city": city,
            "address": address,
            "latitude": candidate.latitude,
            "longitude": candidate.longitude,
            "official_url": official_url,
        }
        changes = [
            FieldChange(field=key, before=None, after=value)
            for key, value in create_kwargs.items()
            if key in {"name", "pref", "city", "address", "official_url"}
        ]
        return GymPlan(
            action="create",
            gym=None,
            slug=slug,
            canonical_id=canonical_id,
            create_kwargs=create_kwargs,
            changes=changes,
        )

    async def _build_equipment_plans(
        self, payload: Any, target_gym: Gym | None
    ) -> list[EquipmentPlan]:
        if not isinstance(payload, Iterable):
            return []
        slots: list[dict[str, Any]] = [slot for slot in payload if isinstance(slot, dict)]
        if not slots:
            return []
        slugs = [slot.get("slug") for slot in slots if isinstance(slot.get("slug"), str)]
        if not slugs:
            return []
        stmt = select(Equipment).where(Equipment.slug.in_(slugs))
        result = await self._session.execute(stmt)
        equipment_map = {eq.slug: eq for eq in result.scalars().all()}
        equipment_ids = [int(eq.id) for eq in equipment_map.values() if eq.id is not None]
        existing_map: dict[int, GymEquipment] = {}
        if target_gym and target_gym.id and equipment_ids:
            eq_stmt = (
                select(GymEquipment)
                .where(GymEquipment.gym_id == target_gym.id)
                .where(GymEquipment.equipment_id.in_(equipment_ids))
            )
            eq_result = await self._session.execute(eq_stmt)
            existing_map = {row.equipment_id: row for row in eq_result.scalars().all()}

        plans: list[EquipmentPlan] = []
        for slot in slots:
            slug = slot.get("slug")
            if not isinstance(slug, str) or not slug:
                continue
            equipment = equipment_map.get(slug)
            if equipment is None:
                plans.append(
                    EquipmentPlan(
                        slug=slug,
                        equipment=None,
                        action="skip",
                        count_before=None,
                        count_after=None,
                        warnings=["unknown equipment slug"],
                    )
                )
                continue
            count_raw = slot.get("count")
            count_value: int | None
            warnings: list[str] = []
            if isinstance(count_raw, int):
                if count_raw < 0:
                    warnings.append("negative count discarded")
                    count_value = None
                else:
                    count_value = count_raw
            else:
                count_value = None
            existing = existing_map.get(int(equipment.id)) if equipment.id is not None else None
            if existing is None:
                plans.append(
                    EquipmentPlan(
                        slug=slug,
                        equipment=equipment,
                        action="insert",
                        count_before=None,
                        count_after=count_value,
                        warnings=warnings,
                    )
                )
                continue
            merged_count: int | None
            if count_value is None:
                merged_count = existing.count
            elif existing.count is None:
                merged_count = count_value
            else:
                merged_count = max(existing.count, count_value)
            plans.append(
                EquipmentPlan(
                    slug=slug,
                    equipment=equipment,
                    action="merge",
                    count_before=existing.count,
                    count_after=merged_count,
                    existing=existing,
                    warnings=warnings,
                )
            )
        return plans

    async def _generate_unique_slug(self, base_slug: str) -> str:
        slug = base_slug
        suffix = 2
        while True:
            stmt = select(Gym).where(Gym.slug == slug)
            result = await self._session.execute(stmt)
            if result.scalar_one_or_none() is None:
                return slug
            slug = f"{base_slug}-{suffix}"
            suffix += 1

    async def _find_gym_by_slug(self, slug: str) -> Gym | None:
        stmt = select(Gym).where(Gym.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_gym_by_center_no(self, center_no: int) -> Gym | None:
        pattern = f"%/sports_center{center_no}/%"
        stmt = select(Gym).where(Gym.official_url.like(pattern))
        result = await self._session.execute(stmt)
        for gym in result.scalars():
            official = gym.official_url or ""
            if _extract_center_no(official) != center_no:
                continue
            base = _to_intro_base_url(official)
            if base and official.rstrip("/") == base.rstrip("/"):
                return gym
        return None

    async def _find_gym_by_official_url(self, url: str) -> Gym | None:
        stmt = select(Gym).where(Gym.official_url == url)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_gym_by_canonical_id(self, canonical_id: str) -> Gym | None:
        stmt = select(Gym).where(Gym.canonical_id == canonical_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


__all__ = [
    "ApproveService",
    "ApproveResponse",
    "ApprovalError",
    "CandidateNotFoundError",
    "CandidateStatusConflictError",
    "InvalidCandidatePayloadError",
]
