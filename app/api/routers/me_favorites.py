from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_session
from app.schemas.favorite import FavoriteCreateRequest, FavoriteItem
from app.services.favorites import FavoriteService

router = APIRouter(prefix="/me", tags=["me"])


@router.post("/favorites", status_code=204, summary="お気に入りを追加（冪等）")
async def add_favorite(
    payload: FavoriteCreateRequest,
    session: AsyncSession = Depends(get_async_session),
):
    svc = FavoriteService(session)
    await svc.add(device_id=payload.device_id, gym_id=payload.gym_id)
    return None


@router.get(
    "/favorites",
    response_model=list[FavoriteItem],
    summary="お気に入り一覧（デバイスID）",
)
async def list_favorites(
    device_id: str = Query(
        ...,
        description="匿名デバイスID",
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
    session: AsyncSession = Depends(get_async_session),
):
    svc = FavoriteService(session)
    items = await svc.list(device_id=device_id)
    return [FavoriteItem(**it) for it in items]


@router.delete("/favorites/{gym_id}", status_code=204, summary="お気に入りを削除（冪等）")
async def delete_favorite(
    gym_id: int,
    device_id: str = Query(
        ...,
        description="匿名デバイスID",
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
    session: AsyncSession = Depends(get_async_session),
):
    svc = FavoriteService(session)
    await svc.remove(device_id=device_id, gym_id=gym_id)
    return None
