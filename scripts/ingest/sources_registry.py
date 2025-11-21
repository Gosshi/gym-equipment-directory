"""Registry of municipal ingest sources for Tokyo wards."""

from __future__ import annotations

import re
from dataclasses import dataclass


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

    def compile_intro_patterns(self) -> list[re.Pattern[str]]:
        return [re.compile(pattern) for pattern in self.intro_patterns]

    def compile_article_patterns(self) -> list[re.Pattern[str]]:
        return [re.compile(pattern) for pattern in self.article_patterns]


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
    ),
    "municipal_tokyo_metropolitan": MunicipalSource(
        title="municipal_tokyo_metropolitan",
        base_url="https://www.metro.tokyo.lg.jp/",
        intro_patterns=[],
        article_patterns=ARTICLE_PAT_DEFAULT,
        list_seeds=[],
        pref_slug="tokyo",
        city_slug="tokyo-metropolitan",
    ),
    # --- Additional wards will be registered here ---
    # "municipal_chuo": MunicipalSource(...),
    # "municipal_minato": MunicipalSource(...),
    # ... up to 23 wards
}


__all__ = ["MunicipalSource", "SOURCES", "ARTICLE_PAT_DEFAULT"]
