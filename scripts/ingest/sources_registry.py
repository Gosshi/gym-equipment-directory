"""Registry of municipal ingest sources for Tokyo wards."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class MunicipalSource:
    """Descriptor for a municipal training room site."""

    title: str
    base_url: str
    intro_patterns: list[str]
    article_patterns: list[str]
    list_seeds: list[str]
    pref_slug: str
    city_slug: str
    parse_hints: dict[str, str] | None = None
    base_urls: tuple[str, ...] | None = None
    start_urls: tuple[str, ...] | None = None
    domain_allowlist: tuple[str, ...] | None = None
    path_allowlist: tuple[str, ...] | None = None
    path_denylist: tuple[str, ...] | None = None
    page_type_patterns: dict[str, tuple[str, ...]] | None = None
    start_url_page_types: dict[str, str] | None = None

    def compile_intro_patterns(self) -> list[re.Pattern[str]]:
        return [re.compile(pattern) for pattern in self.intro_patterns]

    def compile_article_patterns(self) -> list[re.Pattern[str]]:
        return [re.compile(pattern) for pattern in self.article_patterns]

    @property
    def area(self) -> tuple[str, str]:
        return self.pref_slug, self.city_slug

    @property
    def primary_base_url(self) -> str:
        if self.base_urls:
            return self.base_urls[0]
        return self.base_url

    def iter_base_urls(self) -> tuple[str, ...]:
        if self.base_urls:
            return self.base_urls
        return (self.base_url,)

    def iter_start_urls(self) -> tuple[str, ...]:
        if self.start_urls:
            return self.start_urls
        return tuple(self.list_seeds)

    def iter_allowed_domains(self) -> tuple[str, ...]:
        if self.domain_allowlist:
            return self.domain_allowlist
        hosts: set[str] = set()
        for base in self.iter_base_urls():
            parsed = urlparse(base)
            if parsed.netloc:
                hosts.add(parsed.netloc)
        if not hosts:
            parsed = urlparse(self.base_url)
            if parsed.netloc:
                hosts.add(parsed.netloc)
        return tuple(sorted(hosts))

    def compile_path_allowlist(self) -> tuple[re.Pattern[str], ...]:
        patterns = self.path_allowlist or ()
        return tuple(re.compile(pattern) for pattern in patterns)

    def compile_path_denylist(self) -> tuple[re.Pattern[str], ...]:
        patterns = self.path_denylist or ()
        return tuple(re.compile(pattern) for pattern in patterns)

    def compile_page_type_patterns(self) -> dict[str, list[re.Pattern[str]]]:
        compiled: dict[str, list[re.Pattern[str]]] = {}
        mapping = self.page_type_patterns or {}
        for page_type, patterns in mapping.items():
            compiled[page_type] = [re.compile(pattern) for pattern in patterns]
        if not compiled:
            compiled["intro"] = self.compile_intro_patterns()
            compiled["article"] = self.compile_article_patterns()
        return compiled


ARTICLE_PAT_DEFAULT = [
    r"/introduction/post_.*\.html$",
    r"/introduction/tr_detail\.html$",
    r"/introduction/trainingmachine\.html$",
    r"/introduction/notes\.html$",
]


SOURCES: dict[str, MunicipalSource] = {
    "municipal_koto": MunicipalSource(
        title="municipal_koto",
        base_url="https://www.koto-hsc.or.jp/",
        intro_patterns=[r"/sports_center\d+/introduction/?$"],
        article_patterns=ARTICLE_PAT_DEFAULT,
        list_seeds=[
            "/sports_center2/introduction/",
            "/sports_center3/introduction/",
            "/sports_center4/introduction/",
            "/sports_center5/introduction/",
        ],
        pref_slug="tokyo",
        city_slug="koto",
        parse_hints={"center_no_from_url": r"/sports_center(\d+)/"},
        base_urls=("https://www.koto-hsc.or.jp/",),
        start_urls=(
            "https://www.koto-hsc.or.jp/sports_center2/introduction/",
            "https://www.koto-hsc.or.jp/sports_center3/introduction/",
            "https://www.koto-hsc.or.jp/sports_center4/introduction/",
            "https://www.koto-hsc.or.jp/sports_center5/introduction/",
        ),
        domain_allowlist=("www.koto-hsc.or.jp",),
        page_type_patterns={
            "facility": (r"/sports_center\d+/introduction/?$",),
            "article": tuple(ARTICLE_PAT_DEFAULT),
        },
    ),
    "municipal_edogawa": MunicipalSource(
        title="municipal_edogawa",
        base_url="https://www.city.edogawa.tokyo.jp/",
        # 施設「紹介トップ」を拾う（最初は少し緩めでOK）
        intro_patterns=[
            r"/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/.+/index\.html$",
            r"/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/[^/]+\.html$",
        ],
        # お知らせ系は施設新規作成しない（必要に応じて追加）
        article_patterns=ARTICLE_PAT_DEFAULT
        + [
            r"/e028/.*/(news|oshirase|notice)/.*\.html$",
        ],
        list_seeds=[
            "/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/index.html",
            "/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/sogo_sports_center/index.html",
            "/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/shinozaki_plaza/index.html",
            "/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/tobu_health_support/index.html",
        ],
        pref_slug="tokyo",
        city_slug="edogawa",
        parse_hints=None,
        base_urls=("https://www.city.edogawa.tokyo.jp/",),
        start_urls=(
            "https://www.city.edogawa.tokyo.jp/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/index.html",
            "https://www.city.edogawa.tokyo.jp/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/sogo_sports_center/index.html",
            "https://www.city.edogawa.tokyo.jp/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/shinozaki_plaza/index.html",
            "https://www.city.edogawa.tokyo.jp/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/tobu_health_support/index.html",
        ),
        domain_allowlist=("www.city.edogawa.tokyo.jp",),
        page_type_patterns={
            "facility": (
                r"/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/.+/index\.html$",
                r"/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/[^/]+\.html$",
            ),
            "article": tuple(ARTICLE_PAT_DEFAULT) + (r"/e028/.*/(news|oshirase|notice)/.*\.html$",),
        },
    ),
    "municipal_sumida": MunicipalSource(
        title="municipal_sumida",
        base_url="https://www.city.sumida.lg.jp/",
        intro_patterns=[
            r"/sisetu_info/[^/]+/(index\.html|[^/]+\.html)$",
        ],
        article_patterns=ARTICLE_PAT_DEFAULT
        + [
            r"/sisetu_info/.*/(oshirase|news)/.*\.html$",
        ],
        list_seeds=[
            "/sisetu_info/setsubi_kinou/okunaisports.html",
            "/sisetu_info/sports/umewaka.html",
            "/sisetu_info/sports/sumidasportcenter.html",
            "/sisetu_info/sports/sougou-undoujou.html",
            "/sisetu_info/tamokuteki/midori_communityc.html",
        ],
        pref_slug="tokyo",
        city_slug="sumida",
        base_urls=("https://www.city.sumida.lg.jp/",),
        start_urls=(
            "https://www.city.sumida.lg.jp/sisetu_info/setsubi_kinou/okunaisports.html",
            "https://www.city.sumida.lg.jp/sisetu_info/sports/umewaka.html",
            "https://www.city.sumida.lg.jp/sisetu_info/sports/sumidasportcenter.html",
            "https://www.city.sumida.lg.jp/sisetu_info/sports/sougou-undoujou.html",
            "https://www.city.sumida.lg.jp/sisetu_info/tamokuteki/midori_communityc.html",
        ),
        domain_allowlist=("www.city.sumida.lg.jp",),
        page_type_patterns={
            "facility": (r"/sisetu_info/[^/]+/(index\.html|[^/]+\.html)$",),
            "article": tuple(ARTICLE_PAT_DEFAULT) + (r"/sisetu_info/.*/(oshirase|news)/.*\.html$",),
        },
    ),
    "municipal_chuo": MunicipalSource(
        title="municipal_chuo",
        base_url="https://www.city.chuo.lg.jp/",
        intro_patterns=[r"/(kurashi|shisetsu|a[0-9]+)/.*/sports/.+\.html$"],
        article_patterns=ARTICLE_PAT_DEFAULT,
        list_seeds=[
            "/kurashi/kyoiku/sports/index.html",
            "/kurashi/kyoiku/sports/shisetsu/index.html",
            "/shisetsu/sports/",
        ],
        pref_slug="tokyo",
        city_slug="chuo",
        parse_hints=None,
        base_urls=("https://www.city.chuo.lg.jp/",),
        start_urls=(
            "https://www.city.chuo.lg.jp/kurashi/kyoiku/sports/index.html",
            "https://www.city.chuo.lg.jp/kurashi/kyoiku/sports/shisetsu/sogosportscenter/index.html",
            "https://www.city.chuo.lg.jp/shisetsu/sports/sogosportscenter/index.html",
        ),
        domain_allowlist=("www.city.chuo.lg.jp", "city.chuo.lg.jp"),
        path_allowlist=(
            r"^/kurashi/.*/sports/",
            r"^/shisetsu/sports/",
            r"^/a[0-9]+/sports/",
        ),
        path_denylist=(r"/event", r"/reservation", r"/pdf/", r"/oshirase/"),
        page_type_patterns={
            "index": (
                r"/kurashi/.*/sports/(index|ichiran)\.html$",
                r"/shisetsu/sports/index\.html$",
            ),
            "category": (
                r"/kurashi/.*/sports/(category|menu)/.*\.html$",
                r"/shisetsu/sports/.*/category/.*\.html$",
            ),
            "facility": (
                r"/kurashi/.*/sports/.*/(index|detail|shisetsu)\.html$",
                r"/shisetsu/sports/.+/(index|detail|training).*\.html$",
                r"/a[0-9]+/sports/.+/(index|detail).*\.html$",
            ),
            "article": tuple(ARTICLE_PAT_DEFAULT),
        },
        start_url_page_types={
            "https://www.city.chuo.lg.jp/kurashi/kyoiku/sports/index.html": "index",
            (
                "https://www.city.chuo.lg.jp/kurashi/kyoiku/sports/shisetsu/"
                "sogosportscenter/index.html"
            ): "facility",
            "https://www.city.chuo.lg.jp/shisetsu/sports/sogosportscenter/index.html": "facility",
        },
    ),
    "municipal_minato": MunicipalSource(
        title="municipal_minato",
        base_url="https://www.city.minato.tokyo.jp/",
        intro_patterns=[r"/(shisetsu|kurashi|a[0-9]+)/.*/sports/.+\.html$"],
        article_patterns=ARTICLE_PAT_DEFAULT,
        list_seeds=[
            "/shisetsu/sports/",
            "/kurashi/kyoiku/sports/index.html",
        ],
        pref_slug="tokyo",
        city_slug="minato",
        parse_hints=None,
        base_urls=("https://www.city.minato.tokyo.jp/",),
        start_urls=(
            "https://www.city.minato.tokyo.jp/shisetsu/sports/minatosportscenter.html",
            "https://www.city.minato.tokyo.jp/shisetsu/sports/minatosportscenter/trainingroom.html",
            "https://www.city.minato.tokyo.jp/kurashi/kyoiku/sports/index.html",
        ),
        domain_allowlist=("www.city.minato.tokyo.jp", "city.minato.tokyo.jp"),
        path_allowlist=(
            r"^/shisetsu/sports/",
            r"^/kurashi/.*/sports/",
            r"^/a[0-9]+/sports/",
        ),
        path_denylist=(r"/event", r"/news", r"/reservation", r"/oshirase"),
        page_type_patterns={
            "index": (
                r"/shisetsu/sports/index\.html$",
                r"/kurashi/.*/sports/(index|ichiran)\.html$",
            ),
            "category": (
                r"/shisetsu/sports/.*/category/.*\.html$",
                r"/kurashi/.*/sports/.*/category/.*\.html$",
            ),
            "facility": (
                r"/shisetsu/sports/.+/(index|detail|training).*\.html$",
                r"/kurashi/.*/sports/.*/(index|detail|shisetsu)\.html$",
                r"/a[0-9]+/sports/.+/(index|detail).*\.html$",
            ),
            "article": tuple(ARTICLE_PAT_DEFAULT)
            + (r"/(shisetsu|kurashi)/.*/sports/.*/(news|oshirase)/.*\.html$",),
        },
        start_url_page_types={
            "https://www.city.minato.tokyo.jp/shisetsu/sports/minatosportscenter.html": "facility",
            (
                "https://www.city.minato.tokyo.jp/shisetsu/sports/minatosportscenter/"
                "trainingroom.html"
            ): "facility",
            "https://www.city.minato.tokyo.jp/kurashi/kyoiku/sports/index.html": "index",
        },
    ),
}


__all__ = ["MunicipalSource", "SOURCES", "ARTICLE_PAT_DEFAULT"]
