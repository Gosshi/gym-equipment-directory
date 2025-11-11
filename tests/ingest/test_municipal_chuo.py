import pathlib
from collections.abc import Iterable

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.equipment import Equipment
from app.models.gym_candidate import GymCandidate
from app.models.scraped_page import ScrapedPage
from scripts.ingest import fetch_http, normalize, parse

FIXTURE_DIR = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "municipal_chuo"


def _read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _sleep(_: float) -> None:
        return None

    monkeypatch.setattr(fetch_http.asyncio, "sleep", _sleep)


@pytest.fixture(autouse=True)
def _predictable_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch_http.random, "uniform", lambda a, b: a)


def _install_http_stub(
    monkeypatch: pytest.MonkeyPatch,
    responses: dict[str, list[httpx.Response]],
    request_log: list[tuple[str, dict[str, str]]],
) -> None:
    class _StubAsyncClient:
        def __init__(self, **kwargs) -> None:
            self._responses = responses
            self._request_log = request_log
            self._default_headers = dict(kwargs.get("headers") or {})

        async def __aenter__(self) -> "_StubAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(
            self,
            url: str,
            *,
            headers: dict[str, str] | None = None,
            timeout: float | None = None,
        ) -> httpx.Response:
            merged = dict(self._default_headers)
            if headers:
                merged.update(headers)
            self._request_log.append((url, merged))
            queue = self._responses.get(url)
            if queue is None:
                raise AssertionError(f"Unexpected request for {url}")
            if not queue:
                raise AssertionError(f"No queued responses for {url}")
            return queue.pop(0)

    monkeypatch.setattr(fetch_http.httpx, "AsyncClient", _StubAsyncClient)


@pytest.fixture
def _bind_session(monkeypatch: pytest.MonkeyPatch, session: AsyncSession) -> None:
    SessionMaker = async_sessionmaker(
        bind=session.bind, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(fetch_http, "SessionLocal", SessionMaker)
    monkeypatch.setattr(parse, "SessionLocal", SessionMaker)
    monkeypatch.setattr(normalize, "SessionLocal", SessionMaker)


async def _ensure_equipments(session: AsyncSession, slugs: Iterable[str]) -> None:
    for slug in slugs:
        exists = await session.scalar(select(Equipment).where(Equipment.slug == slug))
        if exists:
            continue
        equipment = Equipment(slug=slug, name=slug, category="machine")
        session.add(equipment)
    await session.commit()


@pytest.mark.asyncio
async def test_municipal_chuo_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    session: AsyncSession,
    _bind_session,
) -> None:
    await _ensure_equipments(session, ["treadmill", "lat-pulldown", "dumbbell"])

    monkeypatch.setenv("APP_ENV", "dev")

    robots_url = "https://www.city.chuo.lg.jp/robots.txt"
    index_url = "https://www.city.chuo.lg.jp/sports/index.html"
    category_url = "https://www.city.chuo.lg.jp/sports/category/training.html"
    facility_url = "https://www.city.chuo.lg.jp/sports/center/facility.html"

    responses = {
        robots_url: [httpx.Response(404)],
        index_url: [httpx.Response(200, text=_read_fixture("index.html"))],
        category_url: [httpx.Response(200, text=_read_fixture("category.html"))],
        facility_url: [httpx.Response(200, text=_read_fixture("facility.html"))],
    }
    request_log: list[tuple[str, dict[str, str]]] = []
    _install_http_stub(monkeypatch, responses, request_log)

    await fetch_http.fetch_http_pages(
        "municipal_chuo",
        pref="tokyo",
        city="chuo",
        limit=5,
        min_delay=0.1,
        max_delay=0.2,
        respect_robots=True,
        user_agent="TestAgent/1.0",
        timeout=5.0,
        dry_run=False,
        force=False,
    )

    pages = (await session.execute(select(ScrapedPage))).scalars().all()
    urls = {page.url for page in pages}
    assert urls == {index_url, category_url, facility_url}

    meta_map = {page.url: page.response_meta or {} for page in pages}
    assert meta_map[index_url]["municipal_page_type"] == "index"
    assert meta_map[category_url]["municipal_page_type"] == "category"
    assert meta_map[facility_url]["municipal_page_type"] == "facility"

    await parse.parse_pages("municipal_chuo", limit=10)
    await normalize.normalize_candidates("municipal_chuo", limit=10)

    candidates = (await session.execute(select(GymCandidate))).scalars().all()
    assert len(candidates) == 3

    by_url = {candidate.source_page.url: candidate for candidate in candidates}
    facility_candidate = by_url[facility_url]
    category_candidate = by_url[category_url]
    index_candidate = by_url[index_url]

    assert facility_candidate.pref_slug == "tokyo"
    assert facility_candidate.city_slug == "chuo"
    payload = facility_candidate.parsed_json or {}
    assert payload["meta"]["create_gym"] is True
    assert payload["meta"]["canonical_hint"] == "中央区総合スポーツセンター トレーニングルーム"
    assert payload["equipments_slotted"] == [
        {"slug": "treadmill", "count": 8},
        {"slug": "lat-pulldown", "count": 2},
    ]
    assert payload["equipments_slugs"] == ["treadmill", "lat-pulldown", "dumbbell"]

    assert category_candidate.parsed_json["meta"]["create_gym"] is False
    assert index_candidate.parsed_json["meta"]["create_gym"] is False
