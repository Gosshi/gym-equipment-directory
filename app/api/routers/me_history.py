from __future__ import annotations

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.gym_search import GymSummary

router = APIRouter(prefix="/me", tags=["me"])


class HistoryResponse(BaseModel):
    items: list[GymSummary] = Field(
        default_factory=list, description="閲覧履歴に含まれるジムの要約"
    )


class HistoryRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    gym_id: int | None = Field(default=None, alias="gymId", description="単一ジムID")
    gym_ids: list[int] | None = Field(default=None, alias="gymIds", description="ジムIDのリスト")

    @model_validator(mode="after")
    def _require_any_payload(self) -> HistoryRequest:
        if self.gym_id is None and not (self.gym_ids or []):
            raise ValueError("gymId または gymIds のいずれかを指定してください。")
        return self


@router.get("/history", response_model=HistoryResponse, summary="閲覧履歴を取得")
async def get_history() -> HistoryResponse:
    return HistoryResponse()


@router.post(
    "/history",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="閲覧履歴を登録（冪等）",
    response_class=Response,
)
async def add_history(payload: HistoryRequest) -> Response:  # pragma: no cover - 呼び出しのみ検証
    # 現状はストレージ未実装のため、入力バリデーションのみ行う
    return Response(status_code=status.HTTP_204_NO_CONTENT)
