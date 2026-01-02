"""SEO-optimized slug generation for gym URLs.

Generates hierarchical slugs in the format: {pref}/{city}/{facility-name}
Example: tokyo/suginami/kamiigusa-sports-center
"""

from __future__ import annotations

import re
import unicodedata

# Prefecture name to romaji mapping
PREF_ROMAJI: dict[str, str] = {
    "北海道": "hokkaido",
    "青森県": "aomori",
    "岩手県": "iwate",
    "宮城県": "miyagi",
    "秋田県": "akita",
    "山形県": "yamagata",
    "福島県": "fukushima",
    "茨城県": "ibaraki",
    "栃木県": "tochigi",
    "群馬県": "gunma",
    "埼玉県": "saitama",
    "千葉県": "chiba",
    "東京都": "tokyo",
    "神奈川県": "kanagawa",
    "新潟県": "niigata",
    "富山県": "toyama",
    "石川県": "ishikawa",
    "福井県": "fukui",
    "山梨県": "yamanashi",
    "長野県": "nagano",
    "岐阜県": "gifu",
    "静岡県": "shizuoka",
    "愛知県": "aichi",
    "三重県": "mie",
    "滋賀県": "shiga",
    "京都府": "kyoto",
    "大阪府": "osaka",
    "兵庫県": "hyogo",
    "奈良県": "nara",
    "和歌山県": "wakayama",
    "鳥取県": "tottori",
    "島根県": "shimane",
    "岡山県": "okayama",
    "広島県": "hiroshima",
    "山口県": "yamaguchi",
    "徳島県": "tokushima",
    "香川県": "kagawa",
    "愛媛県": "ehime",
    "高知県": "kochi",
    "福岡県": "fukuoka",
    "佐賀県": "saga",
    "長崎県": "nagasaki",
    "熊本県": "kumamoto",
    "大分県": "oita",
    "宮崎県": "miyazaki",
    "鹿児島県": "kagoshima",
    "沖縄県": "okinawa",
}

# Tokyo 23 wards romaji mapping
TOKYO_WARDS_ROMAJI: dict[str, str] = {
    "千代田区": "chiyoda",
    "中央区": "chuo",
    "港区": "minato",
    "新宿区": "shinjuku",
    "文京区": "bunkyo",
    "台東区": "taito",
    "墨田区": "sumida",
    "江東区": "koto",
    "品川区": "shinagawa",
    "目黒区": "meguro",
    "大田区": "ota",
    "世田谷区": "setagaya",
    "渋谷区": "shibuya",
    "中野区": "nakano",
    "杉並区": "suginami",
    "豊島区": "toshima",
    "北区": "kita",
    "荒川区": "arakawa",
    "板橋区": "itabashi",
    "練馬区": "nerima",
    "足立区": "adachi",
    "葛飾区": "katsushika",
    "江戸川区": "edogawa",
}

# Common Tokyo cities (Tama area) romaji mapping
TOKYO_CITIES_ROMAJI: dict[str, str] = {
    "八王子市": "hachioji",
    "立川市": "tachikawa",
    "武蔵野市": "musashino",
    "三鷹市": "mitaka",
    "青梅市": "ome",
    "府中市": "fuchu",
    "昭島市": "akishima",
    "調布市": "chofu",
    "町田市": "machida",
    "小金井市": "koganei",
    "小平市": "kodaira",
    "日野市": "hino",
    "東村山市": "higashimurayama",
    "国分寺市": "kokubunji",
    "国立市": "kunitachi",
    "福生市": "fussa",
    "狛江市": "komae",
    "東大和市": "higashiyamato",
    "清瀬市": "kiyose",
    "東久留米市": "higashikurume",
    "武蔵村山市": "musashimurayama",
    "多摩市": "tama",
    "稲城市": "inagi",
    "羽村市": "hamura",
    "あきる野市": "akiruno",
    "西東京市": "nishitokyo",
}

# Merge all city mappings
CITY_ROMAJI: dict[str, str] = {**TOKYO_WARDS_ROMAJI, **TOKYO_CITIES_ROMAJI}


def _remove_redundant_location_from_name(name: str, city: str | None) -> str:
    """Remove city/ward name from facility name to avoid redundancy.

    E.g., "杉並区上井草スポーツセンター" with city="杉並区" -> "上井草スポーツセンター"
    E.g., "品川区立総合体育館" with city="品川区" -> "総合体育館"
    E.g., "八王子市民体育館" with city="八王子市" -> "体育館"
    """
    if not city:
        return name

    # Get base name without suffix (区/市/町/村)
    city_base = re.sub(r"[区市町村]$", "", city)
    cleaned = name

    if city_base:
        # Remove patterns like:
        # - "品川区立" -> ""
        # - "八王子市民" -> ""
        # - "杉並区" -> ""
        cleaned = re.sub(rf"{city_base}[区市町村]?[立民]?", "", cleaned)

    # Also remove standalone "立" at the beginning if it's the only prefix left
    cleaned = re.sub(r"^立", "", cleaned)

    return cleaned.strip()


def _slugify_name(value: str, city: str | None = None) -> str:
    """Convert facility name to URL-safe slug using pykakasi for Japanese text.

    Args:
        value: The facility name
        city: Optional city name to remove from the facility name for cleaner slugs
    """
    # Remove redundant location info from name
    cleaned_name = _remove_redundant_location_from_name(value, city)

    try:
        from pykakasi import kakasi

        kks = kakasi()
        result = kks.convert(cleaned_name)
        # Use hepburn romanization with spaces between words
        romaji = " ".join([item["hepburn"] for item in result])
    except ImportError:
        # Fallback: keep only ASCII alphanumeric, spaces and hyphens
        # This will lose Japanese characters but won't crash
        romaji = cleaned_name

    normalized = unicodedata.normalize("NFKC", romaji)
    # Remove non-alphanumeric characters except hyphens and spaces
    # Keep Japanese hiragana/katakana/kanji for fallback detection
    cleaned = re.sub(r"[^0-9A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\s-]", "", normalized)

    # Check if result contains only Japanese (pykakasi not available)
    if re.match(r"^[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\s-]+$", cleaned):
        # pykakasi unavailable and text is pure Japanese - cannot convert
        # Return empty string and let caller handle it
        return ""

    # Remove any remaining Japanese characters for final slug
    cleaned = re.sub(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]", "", cleaned)
    lowered = cleaned.lower()
    tokens = re.split(r"[\s_-]+", lowered)
    slug = "-".join(filter(None, tokens))
    # Limit to 50 chars for facility name part
    return slug[:50].strip("-")


def pref_to_romaji(pref: str | None) -> str | None:
    """Convert prefecture name to romaji."""
    if not pref:
        return None
    return PREF_ROMAJI.get(pref)


def city_to_romaji(city: str | None) -> str | None:
    """Convert city/ward name to romaji.

    Falls back to pykakasi conversion if not in predefined mapping.
    """
    if not city:
        return None

    # Check predefined mappings first
    if city in CITY_ROMAJI:
        return CITY_ROMAJI[city]

    # Fallback: use pykakasi for unknown cities
    try:
        from pykakasi import kakasi

        kks = kakasi()
        result = kks.convert(city)
        romaji = "".join([item["hepburn"] for item in result])
        # Clean up: remove 区/市/町/村 suffix romaji
        romaji = re.sub(r"(ku|shi|machi|cho|mura|son)$", "", romaji)
        return romaji.lower()
    except ImportError:
        return None


def build_hierarchical_slug(
    name: str,
    pref: str | None,
    city: str | None,
) -> str:
    """Build a hierarchical slug: {pref}/{city}/{facility-name}.

    Args:
        name: Facility name (required)
        pref: Prefecture name (e.g., "東京都")
        city: City/ward name (e.g., "杉並区")

    Returns:
        Hierarchical slug like "tokyo/suginami/kamiigusa-sports-center"
        Falls back to flat slug if pref/city not available.

    Raises:
        ValueError: If slug generation fails
    """
    # Pass city to remove redundant location info from facility name
    name_slug = _slugify_name(name, city)
    if not name_slug:
        raise ValueError(f"Failed to generate slug from name: {name}")

    pref_slug = pref_to_romaji(pref)
    city_slug = city_to_romaji(city)

    parts = []
    if pref_slug:
        parts.append(pref_slug)
    if city_slug:
        parts.append(city_slug)
    parts.append(name_slug)

    return "/".join(parts)


def build_flat_slug(
    name: str,
    city: str | None = None,
    pref: str | None = None,
) -> str:
    """Build a flat slug (legacy format): facility-name-city-pref.

    Used for backwards compatibility when hierarchical format is not desired.
    """
    name_slug = _slugify_name(name, city)
    if not name_slug:
        raise ValueError(f"Failed to generate slug from name: {name}")

    parts = [name_slug]
    if city:
        city_slug = city_to_romaji(city)
        if city_slug:
            parts.append(city_slug)
    if pref:
        pref_slug = pref_to_romaji(pref)
        if pref_slug:
            parts.append(pref_slug)

    return "-".join(parts)[:64]
