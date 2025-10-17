from __future__ import annotations

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.equipment import Equipment
from app.models.gym_candidate import GymCandidate
from app.models.scraped_page import ScrapedPage
from scripts.ingest import fetch_http, normalize, parse


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
) -> None:
    class _StubAsyncClient:
        def __init__(self, **kwargs) -> None:
            self._responses = responses
            self._default_headers = dict(kwargs.get("headers") or {})

        async def __aenter__(self) -> _StubAsyncClient:
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
        bind=session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    monkeypatch.setattr(fetch_http, "SessionLocal", SessionMaker)
    monkeypatch.setattr(parse, "SessionLocal", SessionMaker)
    monkeypatch.setattr(normalize, "SessionLocal", SessionMaker)


async def _ensure_equipment(session: AsyncSession, slug: str) -> None:
    exists = await session.scalar(select(Equipment).where(Equipment.slug == slug))
    if exists:
        return
    equipment = Equipment(slug=slug, name=slug, category="machine")
    session.add(equipment)
    await session.commit()


@pytest.mark.asyncio
async def test_municipal_pipeline_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
    session: AsyncSession,
    _bind_session,
) -> None:
    await _ensure_equipment(session, "treadmill")
    await _ensure_equipment(session, "upright-bike")

    robots_url = "https://www.koto-hsc.or.jp/robots.txt"
    intro_url = "https://www.koto-hsc.or.jp/sports_center2/introduction/"
    article_url = "https://www.koto-hsc.or.jp/sports_center2/introduction/trainingmachine.html"

    intro_html = """
    <html>
      <head><title>施設案内｜江東区スポーツセンター</title></head>
      <body>
        <main>
          <h1>施設案内｜江東区スポーツセンター</h1>
          <p>所在地：東京都江東区北砂1-2-3</p>
          <h2>トレーニング設備</h2>
          <ul>
            <li>トレッドミル×５​</li>
            <li>アップライトバイク×３</li>
          </ul>
          <a href="trainingmachine.html">設備紹介</a>
        </main>
      </body>
    </html>
    """

    article_html = """
    <html>
      <head><title>トレーニングマシンの紹介</title></head>
      <body>
        <main>
          <h1>トレーニングマシンの紹介</h1>
          <ul>
            <li>トレッドミル×５</li>
          </ul>
        </main>
      </body>
    </html>
    """

    responses = {
        robots_url: [httpx.Response(404)],
        intro_url: [httpx.Response(200, text=intro_html)],
        article_url: [httpx.Response(200, text=article_html)],
    }
    _install_http_stub(monkeypatch, responses)

    await fetch_http.fetch_http_pages(
        "municipal_koto",
        pref="tokyo",
        city="koto",
        limit=2,
        min_delay=0.1,
        max_delay=0.2,
        respect_robots=True,
        user_agent="TestAgent/1.0",
        timeout=5.0,
        dry_run=False,
        force=False,
    )

    pages = (await session.execute(select(ScrapedPage))).scalars().all()
    assert {page.url for page in pages} == {intro_url, article_url}
    meta_map = {page.url: page.response_meta or {} for page in pages}
    assert meta_map[intro_url]["municipal_page_type"] == "intro"
    assert meta_map[article_url]["municipal_page_type"] == "article"

    await parse.parse_pages("municipal_koto", limit=10)
    candidates = (await session.execute(select(GymCandidate))).scalars().all()
    assert len(candidates) == 2

    await normalize.normalize_candidates("municipal_koto", limit=10)
    normalized = (await session.execute(select(GymCandidate))).scalars().all()
    intro_candidate = next(item for item in normalized if item.source_page.url == intro_url)
    article_candidate = next(item for item in normalized if item.source_page.url == article_url)

    assert intro_candidate.pref_slug == "tokyo"
    assert intro_candidate.city_slug == "koto"
    assert intro_candidate.address_raw == "東京都江東区北砂1-2-3"
    payload = intro_candidate.parsed_json or {}
    assert payload["equipments_slugs"] == ["treadmill", "upright-bike"]
    assert payload["equipments_slotted"] == [
        {"slug": "treadmill", "count": 5},
        {"slug": "upright-bike", "count": 3},
    ]
    assert payload["meta"]["create_gym"] is True

    article_payload = article_candidate.parsed_json or {}
    assert article_candidate.address_raw is None
    assert article_payload["meta"]["create_gym"] is False
    assert article_payload["equipments_slugs"] == ["treadmill"]
