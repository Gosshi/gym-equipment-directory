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
# Batch 2: East Wards
SOURCES["municipal_taito"] = MunicipalSource(
    title="municipal_taito",
    base_url="https://www.city.taito.lg.jp/",
    intro_patterns=[r"/gakushu/sports/sportssisetsuichiran/.*\.html$"],
    article_patterns=ARTICLE_PAT_DEFAULT,
    list_seeds=[
        "https://www.city.taito.lg.jp/gakushu/sports/sportssisetsuichiran/index.html",
    ],
    pref_slug="tokyo",
    city_slug="taito",
)

SOURCES["municipal_sumida"] = MunicipalSource(
    title="municipal_sumida",
    base_url="https://www.city.sumida.lg.jp/",
    intro_patterns=[
        r"/sisetu_info/sports/.*\.html$",
    ],
    article_patterns=ARTICLE_PAT_DEFAULT
    + [
        r"/sisetu_info/.*/(oshirase|news)/.*\.html$",
    ],
    list_seeds=[
        "https://www.city.sumida.lg.jp/sisetu_info/setsubi_kinou/okunaisports.html",
    ],
    pref_slug="tokyo",
    city_slug="sumida",
    allowed_hosts=["www.city.sumida.lg.jp", "www.sumispo.com"],
)

SOURCES["municipal_koto"] = MunicipalSource(
    title="municipal_koto",
    base_url="https://www.koto-hsc.or.jp/",
    intro_patterns=[r"/sports_center\d+/introduction/?$"],
    article_patterns=ARTICLE_PAT_DEFAULT + [r"/introduction/detail\.php\?stj_id=\d+"],
    list_seeds=[
        "https://www.koto-hsc.or.jp/sports_center2/introduction/",
        "https://www.koto-hsc.or.jp/sports_center3/introduction/",
        "https://www.koto-hsc.or.jp/sports_center4/introduction/",
        "https://www.koto-hsc.or.jp/sports_center5/introduction/",
    ],
    pref_slug="tokyo",
    city_slug="koto",
    parse_hints={"center_no_from_url": r"/sports_center(\d+)/"},
)

SOURCES["municipal_arakawa"] = MunicipalSource(
    title="municipal_arakawa",
    base_url="https://www.city.arakawa.tokyo.jp/",
    intro_patterns=[r"/a017/sport/.*\.html$"],
    article_patterns=ARTICLE_PAT_DEFAULT,
    list_seeds=[
        "https://www.city.arakawa.tokyo.jp/shisetsuannai/koukyoushisetsu/index.html",
        "https://www.city.arakawa.tokyo.jp/a017/sport/shisetsuriyou/s-centerriyou.html",
    ],
    pref_slug="tokyo",
    city_slug="arakawa",
)

SOURCES["municipal_adachi"] = MunicipalSource(
    title="municipal_adachi",
    base_url="https://www.city.adachi.tokyo.jp/",
    intro_patterns=[r"/sports/shisetsu/koen/.*\.html$"],
    article_patterns=ARTICLE_PAT_DEFAULT,
    list_seeds=[
        "https://www.city.adachi.tokyo.jp/shisetsu/sports/index.html",
    ],
    pref_slug="tokyo",
    city_slug="adachi",
)

SOURCES["municipal_katsushika"] = MunicipalSource(
    title="municipal_katsushika",
    base_url="https://spo.katsushika-web.net/",
    intro_patterns=[r"/facility/[^/]+/$"],
    article_patterns=ARTICLE_PAT_DEFAULT,
    list_seeds=[
        "https://spo.katsushika-web.net/facility/",
    ],
    pref_slug="tokyo",
    city_slug="katsushika",
)

SOURCES["municipal_edogawa"] = MunicipalSource(
    title="municipal_edogawa",
    base_url="https://www.city.edogawa.tokyo.jp",
    intro_patterns=[
        r"/e028/.+/(index\.html|trainingmachine\.html)$",
    ],
    article_patterns=ARTICLE_PAT_DEFAULT
    + [
        r"/e028/.+/(post_\d+\.html|tr_detail\.html)$",
    ],
    list_seeds=[
        "https://www.city.edogawa.tokyo.jp/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/index.html",
    ],
    pref_slug="tokyo",
    city_slug="edogawa",
    parse_hints=None,
)

# Batch 3: South/West Wards
SOURCES["municipal_shinagawa"] = MunicipalSource(
    title="shinagawa",
    base_url="https://www.city.shinagawa.tokyo.jp",
    intro_patterns=[
        r"/PC/shisetsu/shisetsu-bunka/shisetsu-bunka-sprots/.*\.html$",
        r"/PC/shisetsu/shisetsu-bunka/shisetsu-bunka-sprots/.*/index\.html$",
    ],
    article_patterns=[
        r"/PC/shisetsu/shisetsu-bunka/shisetsu-bunka-sprots/.+\.html$",
        r"/PC/shisetsu/shisetsu-bunka/shisetsu-bunka-sprots/.+/.+\.html$",
    ],
    list_seeds=[
        "https://www.city.shinagawa.tokyo.jp/PC/shisetsu/shisetsu-bunka/shisetsu-bunka-sprots/index.html",
    ],
    pref_slug="tokyo",
    city_slug="shinagawa",
)

SOURCES["municipal_meguro"] = MunicipalSource(
    title="meguro",
    base_url="https://www.city.meguro.tokyo.jp",
    intro_patterns=[
        r"/shisetsu/shisetsu/sports_shisetsu/.*\.html$",
        r"/sports/shisetsu/sports/.*\.html$",
    ],
    article_patterns=[
        r"/sports/shisetsu/sports/.+\.html$",
    ],
    list_seeds=[
        "https://www.city.meguro.tokyo.jp/shisetsu/shisetsu/sports_shisetsu/index.html",
    ],
    pref_slug="tokyo",
    city_slug="meguro",
)

SOURCES["municipal_ota"] = MunicipalSource(
    title="ota",
    base_url="https://www.city.ota.tokyo.jp",
    intro_patterns=[
        r"/shisetsu/sports/.*\.html$",
    ],
    article_patterns=[
        r"/shisetsu/sports/.+\.html$",
    ],
    list_seeds=[
        "https://www.city.ota.tokyo.jp/shisetsu/sports/index.html",
    ],
    pref_slug="tokyo",
    city_slug="ota",
)

SOURCES["municipal_setagaya"] = MunicipalSource(
    title="setagaya",
    base_url="https://www.city.setagaya.lg.jp",
    intro_patterns=[
        r"/bunkakankou/.*\.html$",
        r"/bunkasports/sportsrecreation/.*\.html$",
    ],
    article_patterns=[
        r"/bunkasports/sportsrecreation/.+\.html$",
    ],
    list_seeds=[
        "https://www.city.setagaya.lg.jp/bunkasports/sportsrecreation/category/11820.html",
    ],
    pref_slug="tokyo",
    city_slug="setagaya",
)

SOURCES["municipal_shibuya"] = MunicipalSource(
    title="shibuya",
    base_url="https://www.city.shibuya.tokyo.jp",
    intro_patterns=[
        r"/shisetsu/sports-shisetsu/sports-center/.*\.html$",
    ],
    article_patterns=[
        r"/shisetsu/sports-shisetsu/sports-center/.+\.html$",
    ],
    list_seeds=[
        "https://www.city.shibuya.tokyo.jp/shisetsu/sports-shisetsu/sports-center/",
    ],
    pref_slug="tokyo",
    city_slug="shibuya",
)

SOURCES["municipal_nakano"] = MunicipalSource(
    title="nakano",
    base_url="https://www.city.tokyo-nakano.lg.jp",
    intro_patterns=[
        r"/shisetsu/bunka/sports/.*\.html$",
    ],
    article_patterns=[
        r"/shisetsu/bunka/sports/.+\.html$",
    ],
    list_seeds=[
        "https://www.city.tokyo-nakano.lg.jp/shisetsu/bunka/sports/index.html",
    ],
    pref_slug="tokyo",
    city_slug="nakano",
)

SOURCES["municipal_suginami"] = MunicipalSource(
    title="suginami",
    base_url="https://www.city.suginami.tokyo.jp",
    intro_patterns=[
        r"/kusei/gaiyou/shisetsu/genre/sports/.*\.html$",
    ],
    article_patterns=[
        r"/kusei/gaiyou/shisetsu/genre/sports/.+\.html$",
    ],
    list_seeds=[
        "https://www.city.suginami.tokyo.jp/shisetsu/sports/index.html",
    ],
    pref_slug="tokyo",
    city_slug="suginami",
)

# Batch 4: North Wards
SOURCES["municipal_toshima"] = MunicipalSource(
    title="municipal_toshima",
    base_url="https://www.city.toshima.lg.jp",
    intro_patterns=[
        r"/501/bunka/sports/sports/003418/.*\.html$",
        r"/501/bunka/sports/sports/.*\.html$",
    ],
    article_patterns=[
        r"/501/bunka/sports/sports/003418/.+\.html$",
        r"/501/bunka/sports/sports/.+\.html$",
        r"/501/\d+\.html$",  # For Chihaya Sports Field
    ],
    list_seeds=[
        "https://www.city.toshima.lg.jp/501/bunka/sports/sports/003418/index.html",
    ],
    pref_slug="tokyo",
    city_slug="toshima",
)

SOURCES["municipal_kita"] = MunicipalSource(
    title="municipal_kita",
    base_url="https://www.city.kita.lg.jp",
    intro_patterns=[
        r"/city-information/facilities/1015927/.*\.html$",
        r"/culture-tourism-sports/sports/.*\.html$",
    ],
    article_patterns=[
        r"/culture-tourism-sports/sports/.+\.html$",
        r"/city-information/facilities/.+/1018350/.+\.html$",
    ],
    list_seeds=[
        "https://www.city.kita.lg.jp/city-information/facilities/1015927/index.html",
    ],
    pref_slug="tokyo",
    city_slug="kita",
)

SOURCES["municipal_itabashi"] = MunicipalSource(
    title="municipal_itabashi",
    base_url="https://www.city.itabashi.tokyo.jp",
    intro_patterns=[
        r"/bunka/1005245/.*\.html$",
        r"/shisetsu/sports/.*\.html$",
    ],
    article_patterns=[
        r"/bunka/1005245/.+\.html$",
        r"/shisetsu/sports/.+\.html$",
    ],
    list_seeds=[
        "https://www.city.itabashi.tokyo.jp/bunka/1005245/index.html",
    ],
    pref_slug="tokyo",
    city_slug="itabashi",
)

SOURCES["municipal_nerima"] = MunicipalSource(
    title="municipal_nerima",
    base_url="https://www.city.nerima.tokyo.jp",
    intro_patterns=[
        r"/shisetsu/koen/.*\.html$",
    ],
    article_patterns=[
        r"/shisetsu/koen/.+/.+\.html$",  # Require subdirectory to avoid index.html
    ],
    list_seeds=[
        "https://www.city.nerima.tokyo.jp/shisetsu/koen/index.html",
    ],
    pref_slug="tokyo",
    city_slug="nerima",
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

SOURCES["municipal_taito"] = MunicipalSource(
    title="municipal_taito",
    base_url="https://www.city.taito.lg.jp/",
    intro_patterns=[
        r"/kusei/shisetsu/sports/.*\.html$",
        r"/riverside/.*",  # For taitogeibun.net
    ],
    article_patterns=ARTICLE_PAT_DEFAULT,
    list_seeds=[
        "https://www.taitogeibun.net/riverside/",
        "https://www.city.taito.lg.jp/kusei/shisetsu/sports/shogaigakushu.html",
        "https://www.city.taito.lg.jp/kusei/shisetsu/sports/kuminkan.html",
    ],
    pref_slug="tokyo",
    city_slug="taito",
    allowed_hosts=["www.city.taito.lg.jp", "www.taitogeibun.net"],
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
