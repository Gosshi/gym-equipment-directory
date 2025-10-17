"""Registry of municipal ingest sources for Tokyo wards."""

from __future__ import annotations

from dataclasses import dataclass
import re


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
        intro_patterns=[r"/e078/sports/trainingroom/.*\.html$"],
        article_patterns=ARTICLE_PAT_DEFAULT
        + [r"/e078/sports/.*/(news|notice)/.*\.html$"],
        list_seeds=[
            "/e078/sports/trainingroom/index.html",
            "/e078/sports/trainingroom/sogo_sports_center.html",
            "/e078/sports/trainingroom/shinozaki_plaza.html",
            "/e078/sports/trainingroom/tobu_health_support.html",
        ],
        pref_slug="tokyo",
        city_slug="edogawa",
        parse_hints=None,
    ),
    "municipal_sumida": MunicipalSource(
        title="municipal_sumida",
        base_url="https://www.city.sumida.lg.jp/",
        intro_patterns=[r"/sports/facility/training/.*\.html$"],
        article_patterns=ARTICLE_PAT_DEFAULT
        + [r"/sports/.*/(oshirase|news)/.*\.html$"],
        list_seeds=[
            "/sports/facility/training/sports_center.html",
            "/sports/facility/training/edogawa_gym.html",
            "/sports/facility/training/hikifune_center.html",
        ],
        pref_slug="tokyo",
        city_slug="sumida",
        parse_hints=None,
    ),
    # --- Additional wards will be registered here ---
    # "municipal_chuo": MunicipalSource(...),
    # "municipal_minato": MunicipalSource(...),
    # ... up to 23 wards
}


__all__ = ["MunicipalSource", "SOURCES", "ARTICLE_PAT_DEFAULT"]
