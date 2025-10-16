from __future__ import annotations

from hashlib import sha256

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.scraped_page import ScrapedPage
from scripts.ingest import fetch_http
from scripts.ingest.sites import municipal_koto, site_a


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
            merged = dict(self._default_headers)
            if headers:
                merged.update(headers)
            self._request_log.append((url, merged))
            queue = self._responses.get(url)
            if queue is None:
                msg = f"Unexpected request for {url}"
                raise AssertionError(msg)
            if not queue:
                msg = f"No queued responses for {url}"
                raise AssertionError(msg)
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


@pytest.mark.asyncio
async def test_fetch_http_dry_run_lists_urls(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setenv("APP_ENV", "dev")
    listing_html = """
    <html>
      <body>
        <a class="gym-link" href="/gyms/chiba/funabashi/alpha">Alpha</a>
        <a class="gym-link" href="/gyms/chiba/funabashi/bravo">Bravo</a>
        <a class="gym-link" href="/gyms/chiba/funabashi/charlie">Charlie</a>
        <a class="gym-link" href="/gyms/chiba/funabashi/delta">Delta</a>
        <a class="gym-link" href="/gyms/chiba/funabashi/echo">Echo</a>
      </body>
    </html>
    """
    robots_url = f"{site_a.BASE_URL}/robots.txt"
    listing_url = site_a.build_listing_url("chiba", "funabashi", 1)
    responses = {
        robots_url: [httpx.Response(200, text="User-agent: *\nAllow: /\n")],
        listing_url: [httpx.Response(200, text=listing_html)],
    }
    request_log: list[tuple[str, dict[str, str]]] = []
    _install_http_stub(monkeypatch, responses, request_log)

    await fetch_http.fetch_http_pages(
        "site_a",
        pref="chiba",
        city="funabashi",
        limit=5,
        min_delay=0.1,
        max_delay=0.2,
        respect_robots=True,
        user_agent="TestAgent/1.0",
        timeout=5.0,
        dry_run=True,
        force=False,
    )

    output = capsys.readouterr().out.strip().splitlines()
    assert output == [
        site_a.build_detail_url("chiba", "funabashi", slug)
        for slug in ["alpha", "bravo", "charlie", "delta", "echo"]
    ]


def test_resolve_limit_bounds() -> None:
    assert fetch_http._resolve_limit(None, "dev") == 20
    assert fetch_http._resolve_limit(50, "dev") == 50
    with pytest.raises(ValueError):
        fetch_http._resolve_limit(0, "dev")
    with pytest.raises(ValueError):
        fetch_http._resolve_limit(51, "dev")

    assert fetch_http._resolve_limit(None, "prod") == 20
    assert fetch_http._resolve_limit(20, "prod") == 20
    with pytest.raises(ValueError):
        fetch_http._resolve_limit(21, "prod")


@pytest.mark.asyncio
async def test_fetch_http_respects_robots(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "dev")
    robots_url = f"{site_a.BASE_URL}/robots.txt"
    responses = {
        robots_url: [httpx.Response(200, text="User-agent: *\nDisallow: /gyms/\n")],
    }
    request_log: list[tuple[str, dict[str, str]]] = []
    _install_http_stub(monkeypatch, responses, request_log)

    result = await fetch_http.fetch_http_pages(
        "site_a",
        pref="chiba",
        city="funabashi",
        limit=3,
        min_delay=0.1,
        max_delay=0.2,
        respect_robots=True,
        user_agent="TestAgent/1.0",
        timeout=5.0,
        dry_run=True,
        force=False,
    )

    assert result == 0
    # Only robots.txt should be requested.
    assert [url for url, _ in request_log] == [robots_url]


@pytest.mark.asyncio
async def test_fetch_http_persists_scraped_pages(
    monkeypatch: pytest.MonkeyPatch,
    session: AsyncSession,
    _bind_session,
):
    monkeypatch.setenv("APP_ENV", "dev")
    robots_url = f"{site_a.BASE_URL}/robots.txt"
    listing_url = site_a.build_listing_url("chiba", "funabashi", 1)
    detail_url = site_a.build_detail_url("chiba", "funabashi", "alpha")
    detail_html = "<html><body><h1>Alpha</h1></body></html>"
    single_link_listing = (
        '<html><body><a class="gym-link" href="/gyms/chiba/funabashi/alpha">Alpha</a></body></html>'
    )
    responses = {
        robots_url: [httpx.Response(200, text="User-agent: *\nAllow: /\n")],
        listing_url: [httpx.Response(200, text=single_link_listing)],
        detail_url: [
            httpx.Response(
                200,
                text=detail_html,
                headers={
                    "ETag": '"alpha-etag"',
                    "Last-Modified": "Tue, 01 Oct 2024 10:00:00 GMT",
                },
            )
        ],
    }
    request_log: list[tuple[str, dict[str, str]]] = []
    _install_http_stub(monkeypatch, responses, request_log)

    await fetch_http.fetch_http_pages(
        "site_a",
        pref="chiba",
        city="funabashi",
        limit=1,
        min_delay=0.1,
        max_delay=0.2,
        respect_robots=True,
        user_agent="TestAgent/1.0",
        timeout=5.0,
        dry_run=False,
        force=False,
    )

    result = await session.execute(select(ScrapedPage))
    pages = result.scalars().all()
    assert len(pages) == 1
    page = pages[0]
    assert page.url == detail_url
    assert page.http_status == 200
    assert page.raw_html == detail_html
    assert page.response_meta == {
        "etag": '"alpha-etag"',
        "last_modified": "Tue, 01 Oct 2024 10:00:00 GMT",
    }
    assert page.content_hash == sha256(detail_html.encode("utf-8")).hexdigest()
    first_fetched_at = page.fetched_at

    # Second run to exercise 304 handling and conditional headers.
    second_responses = {
        robots_url: [httpx.Response(200, text="User-agent: *\nAllow: /\n")],
        listing_url: [httpx.Response(200, text=single_link_listing)],
        detail_url: [httpx.Response(304, headers={"ETag": '"alpha-etag"'})],
    }
    second_log: list[tuple[str, dict[str, str]]] = []
    _install_http_stub(monkeypatch, second_responses, second_log)

    await fetch_http.fetch_http_pages(
        "site_a",
        pref="chiba",
        city="funabashi",
        limit=1,
        min_delay=0.1,
        max_delay=0.2,
        respect_robots=True,
        user_agent="TestAgent/1.0",
        timeout=5.0,
        dry_run=False,
        force=False,
    )

    await session.refresh(page)
    assert page.http_status == 304
    assert page.raw_html == detail_html
    assert page.fetched_at > first_fetched_at
    assert page.response_meta.get("etag") == '"alpha-etag"'

    conditional_headers = [headers for url, headers in second_log if url == detail_url]
    assert conditional_headers
    assert conditional_headers[0]["If-None-Match"] == '"alpha-etag"'


@pytest.mark.asyncio
async def test_municipal_koto_crawler_collects_directory_pages(
    monkeypatch: pytest.MonkeyPatch,
    capsys,
):
    monkeypatch.setenv("APP_ENV", "dev")
    robots_url = f"{municipal_koto.BASE_URL}/robots.txt"
    directory_url = f"{municipal_koto.BASE_URL}/sports_center4/introduction/"
    directory_html = """
    <html>
      <body>
        <a href="tr_detail.html">詳細</a>
        <a href="trainingmachine.html">マシン</a>
        <a href="post_18.html">投稿</a>
        <a href="custom-note.html">カスタム</a>
        <a href="/sports_center4/event.html">イベント</a>
        <a href="/sports_center5/introduction/trainingmachine.html">他施設</a>
      </body>
    </html>
    """
    responses = {
        robots_url: [httpx.Response(200, text="User-agent: *\nAllow: /\n")],
        directory_url: [httpx.Response(200, text=directory_html)],
    }
    request_log: list[tuple[str, dict[str, str]]] = []
    _install_http_stub(monkeypatch, responses, request_log)

    await fetch_http.fetch_http_pages(
        municipal_koto.SITE_ID,
        pref="tokyo",
        city="koto",
        limit=10,
        min_delay=0.1,
        max_delay=0.2,
        respect_robots=True,
        user_agent="TestAgent/1.0",
        timeout=5.0,
        dry_run=True,
        force=False,
    )

    output = [line.strip() for line in capsys.readouterr().out.strip().splitlines() if line.strip()]
    assert output == [
        directory_url,
        f"{directory_url}tr_detail.html",
        f"{directory_url}trainingmachine.html",
        f"{directory_url}post_18.html",
        f"{directory_url}custom-note.html",
    ]
