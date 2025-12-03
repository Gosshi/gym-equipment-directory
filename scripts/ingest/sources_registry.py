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
    allowed_hosts: list[str] | None = None

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


WARDS = [
    ("chiyoda", "https://www.city.chiyoda.lg.jp/"),
    ("chuo", "https://www.city.chuo.lg.jp/"),
    ("minato", "https://www.city.minato.tokyo.jp/"),
    ("shinjuku", "https://www.city.shinjuku.lg.jp/"),
    ("bunkyo", "https://www.city.bunkyo.lg.jp/"),
    ("taito", "https://www.city.taito.lg.jp/"),
    ("sumida", "https://www.city.sumida.lg.jp/"),
    ("koto", "https://www.koto-hsc.or.jp/"),
    ("shinagawa", "https://www.city.shinagawa.tokyo.jp/"),
    ("meguro", "https://www.city.meguro.tokyo.jp/"),
    ("ota", "https://www.city.ota.tokyo.jp/"),
    ("setagaya", "https://www.city.setagaya.lg.jp/"),
    ("shibuya", "https://www.city.shibuya.tokyo.jp/"),
    ("nakano", "https://www.city.nakano.tokyo.jp/"),
    ("suginami", "https://www.city.suginami.tokyo.jp/"),
    ("toshima", "https://www.city.toshima.lg.jp/"),
    ("kita", "https://www.city.kita.tokyo.jp/"),
    ("arakawa", "https://www.city.arakawa.tokyo.jp/"),
    ("itabashi", "https://www.city.itabashi.tokyo.jp/"),
    ("nerima", "https://www.city.nerima.tokyo.jp/"),
    ("adachi", "https://www.city.adachi.tokyo.jp/"),
    ("katsushika", "https://www.city.katsushika.lg.jp/"),
    ("edogawa", "https://www.city.edogawa.tokyo.jp/"),
]

SOURCES: dict[str, MunicipalSource] = {}

# 1. Register specific implementations first (overrides)
SOURCES["municipal_koto"] = MunicipalSource(
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
)

SOURCES["municipal_edogawa"] = MunicipalSource(
    title="municipal_edogawa",
    base_url="https://www.city.edogawa.tokyo.jp/",
    intro_patterns=[
        r"/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/.+/index\.html$",
        r"/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/[^/]+\.html$",
    ],
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
)

SOURCES["municipal_sumida"] = MunicipalSource(
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
        "https://www.sumispo.com/facility/training/",
    ],
    pref_slug="tokyo",
    city_slug="sumida",
    allowed_hosts=["www.city.sumida.lg.jp", "www.sumispo.com"],
)

SOURCES["municipal_tokyo_metropolitan"] = MunicipalSource(
    title="municipal_tokyo_metropolitan",
    base_url="https://www.metro.tokyo.lg.jp/",
    intro_patterns=[],
    article_patterns=ARTICLE_PAT_DEFAULT,
    list_seeds=[],
    pref_slug="tokyo",
    city_slug="tokyo-metropolitan",
)

# Batch 1: Central Wards
SOURCES["municipal_chiyoda"] = MunicipalSource(
    title="municipal_chiyoda",
    base_url="https://www.city.chiyoda.lg.jp/",
    intro_patterns=[r"/koho/bunka/sports/shisetsu/.*\.html$"],
    article_patterns=ARTICLE_PAT_DEFAULT,
    list_seeds=[
        "https://www.city.chiyoda.lg.jp/koho/bunka/sports/tairyoku.html",
    ],
    pref_slug="tokyo",
    city_slug="chiyoda",
)

SOURCES["municipal_chuo"] = MunicipalSource(
    title="municipal_chuo",
    base_url="https://www.city.chuo.lg.jp/",
    intro_patterns=[r"/bunkakankou/.*\.html$"],
    article_patterns=ARTICLE_PAT_DEFAULT,
    list_seeds=[
        "https://www.city.chuo.lg.jp/bunkakankou/index.html",
    ],
    pref_slug="tokyo",
    city_slug="chuo",
)

SOURCES["municipal_minato"] = MunicipalSource(
    title="municipal_minato",
    base_url="https://www.city.minato.tokyo.jp/",
    intro_patterns=[r"/map/.*\.html$", r"/shisetsu/sports/.*\.html$"],
    article_patterns=ARTICLE_PAT_DEFAULT,
    list_seeds=[
        "https://www.city.minato.tokyo.jp/map/top.html",
    ],
    pref_slug="tokyo",
    city_slug="minato",
)

SOURCES["municipal_shinjuku"] = MunicipalSource(
    title="municipal_shinjuku",
    base_url="https://www.city.shinjuku.lg.jp/",
    intro_patterns=[r"/kenkou/.*\.html$", r"/shisetsu/.*\.html$"],
    article_patterns=ARTICLE_PAT_DEFAULT,
    list_seeds=[
        "https://www.city.shinjuku.lg.jp/kenkou/index.html",
    ],
    pref_slug="tokyo",
    city_slug="shinjuku",
)

SOURCES["municipal_bunkyo"] = MunicipalSource(
    title="municipal_bunkyo",
    base_url="https://www.city.bunkyo.lg.jp/",
    intro_patterns=[r"/kuseijouhou/shisetsu/.*\.html$"],
    article_patterns=ARTICLE_PAT_DEFAULT,
    list_seeds=[
        "https://www.city.bunkyo.lg.jp/kuseijouhou/shisetsu/index.html",
    ],
    pref_slug="tokyo",
    city_slug="bunkyo",
)

# 2. Register generic/placeholder implementations for remaining wards
for slug, base_url in WARDS:
    key = f"municipal_{slug}"
    if key in SOURCES:
        continue

    SOURCES[key] = MunicipalSource(
        title=key,
        base_url=base_url,
        intro_patterns=[],
        article_patterns=ARTICLE_PAT_DEFAULT,
        list_seeds=[],
        pref_slug="tokyo",
        city_slug=slug,
    )


__all__ = ["MunicipalSource", "SOURCES", "ARTICLE_PAT_DEFAULT"]
