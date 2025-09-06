# app/api/deps.py
from typing import List, Optional
from fastapi import Request

__all__ = ["get_equipment_slugs_from_query"]


def get_equipment_slugs_from_query(
    request: Request,
    equipments: Optional[str] = None
) -> List[str]:
    """
    クエリパラメータから equipments=CSV, equipment=..., equipment[]=... を吸収してスラッグ一覧を返す。
    """
    qp = request.query_params
    slugs: List[str] = []

    # equipment=... の繰り返し
    slugs += qp.getlist("equipment")

    # equipment[]=... の繰り返し
    slugs += qp.getlist("equipment[]")

    # equipments=csv のケース
    if equipments:
        slugs += [s.strip() for s in equipments.split(",") if s.strip()]

    # 空文字除去 & 重複排除（順序保持）
    seen = set()
    out: List[str] = []
    for s in slugs:
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    return out
