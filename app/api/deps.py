# app/api/deps.py
from typing import List
from fastapi import Request

__all__ = ["get_equipment_slugs_from_query"]


def get_equipment_slugs_from_query(request: Request) -> List[str]:
    """
    クエリパラメータから equipment と equipment[] を両方受け取り、重複を排除して返す。

    例:
        ?equipment=bench_press&equipment=lat_pulldown&equipment[]=lat_pulldown&equipment[]=squat
        -> ["bench_press", "lat_pulldown", "squat"]
    """
    qp = request.query_params
    slugs: List[str] = []

    # equipment=... の繰り返し
    slugs += qp.getlist("equipment")

    # equipment[]=... の繰り返し
    slugs += qp.getlist("equipment[]")

    # 空文字や余計な空白を除去
    slugs = [s.strip() for s in slugs if s and s.strip()]

    # 順序維持しつつ重複排除
    seen = set()
    out: List[str] = []
    for s in slugs:
        if s not in seen:
            seen.add(s)
            out.append(s)

    return out
