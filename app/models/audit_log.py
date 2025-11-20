from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class AuditLog(Base):
    """Admin操作の監査ログ (バルク承認/却下など)。

    粒度: 1レコード = 1操作 (複数候補IDをまとめて処理)。
    - action: "bulk_approve" | "bulk_reject"
    - operator: トークン主体 (ADMIN_UI_TOKEN など)
    - candidate_ids: 対象候補ID列 (処理順)
    - success_ids / failure_ids: 結果分類
    - reason: 却下理由 (bulk_reject時) / 任意メモ
    - dry_run: Trueなら処理はロールバックされている
    - created_at: タイムスタンプ
    - request_meta: 追加メタ (IP 等を将来拡張)
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    operator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    candidate_ids: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    success_ids: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    failure_ids: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    dry_run: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    request_meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # NOTE: updated_at 不要 (監査レコードは変更しない前提)


__all__ = ["AuditLog"]
