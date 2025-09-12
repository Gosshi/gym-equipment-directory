from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.report_repository import ReportRepository
from app.schemas.report import (
    ReportAdminItem,
    ReportAdminListResponse,
    ReportCreateRequest,
    decode_cursor,
    encode_cursor,
)

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ReportRepository(session)
        self.session = session

    async def create_for_gym_slug(self, slug: str, payload: ReportCreateRequest) -> dict:
        gym = await self.repo.get_gym_by_slug(slug)
        if not gym:
            raise ValueError("gym not found")
        r = await self.repo.create(
            gym_id=int(gym.id),
            type=payload.type.value,
            message=payload.message,
            email=str(payload.email) if payload.email else None,
            source_url=payload.source_url,
        )
        # Persist the report
        await self.session.commit()
        # Logging: gym_id and type
        logger.info("report accepted", extra={"gym_id": gym.id, "type": payload.type.value})
        return {"id": int(r.id), "status": r.status}

    async def admin_list(
        self, *, status: str, limit: int, cursor_token: str | None
    ) -> ReportAdminListResponse:
        cursor = None
        if cursor_token:
            cursor = decode_cursor(cursor_token)
        items, next_cursor = await self.repo.list_by_status_keyset(
            status=status, limit=limit, cursor=cursor
        )
        out_items: list[ReportAdminItem] = []
        for it, gym in items:
            out_items.append(
                ReportAdminItem(
                    id=int(it.id),
                    gym_id=int(it.gym_id),
                    gym_slug=str(getattr(gym, "slug", "")),
                    type=it.type,  # type: ignore[arg-type]
                    message=it.message,
                    email=it.email,
                    source_url=it.source_url,
                    status=it.status,
                    created_at=it.created_at.isoformat()
                    if isinstance(it.created_at, datetime)
                    else str(it.created_at),
                )
            )
        next_token = encode_cursor(next_cursor[0], next_cursor[1]) if next_cursor else None
        return ReportAdminListResponse(items=out_items, next_cursor=next_token)

    async def resolve(self, report_id: int) -> dict:
        r = await self.repo.resolve(report_id)
        if not r:
            raise ValueError("report not found")
        await self.session.commit()
        return {"id": int(r.id), "status": r.status}
