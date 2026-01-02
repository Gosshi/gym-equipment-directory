"""LLM-based facility description generator for SEO.

Generates natural language descriptions based on facility data.
"""

from __future__ import annotations

import structlog

from app.utils.openai_client import OpenAIClientWrapper

logger = structlog.get_logger(__name__)

# Category labels in Japanese
CATEGORY_LABELS = {
    "gym": "トレーニングルーム",
    "pool": "プール",
    "court": "テニスコート",
    "hall": "体育館",
    "field": "グラウンド",
    "martial_arts": "武道場",
    "archery": "弓道場",
}


def _format_categories(categories: list[str] | None) -> str:
    """Format categories as Japanese labels."""
    if not categories:
        return ""
    labels = [CATEGORY_LABELS.get(cat, cat) for cat in categories]
    return "、".join(labels)


def _format_pools(pools: list[dict] | None) -> str:
    """Format pool information."""
    if not pools:
        return ""
    pool_info = []
    for pool in pools:
        parts = []
        if pool.get("length_m"):
            parts.append(f"{pool['length_m']}m")
        if pool.get("lanes"):
            parts.append(f"{pool['lanes']}レーン")
        if pool.get("heated"):
            parts.append("温水")
        if parts:
            pool_info.append("・".join(parts))
    return "、".join(pool_info)


def _format_courts(courts: list[dict] | None) -> str:
    """Format court information."""
    if not courts:
        return ""
    court_info = []
    for court in courts:
        parts = []
        if court.get("court_type"):
            parts.append(court["court_type"])
        if court.get("courts"):
            parts.append(f"{court['courts']}面")
        if court.get("surface"):
            parts.append(court["surface"])
        if parts:
            court_info.append("・".join(parts))
    return "、".join(court_info)


def _format_opening_hours(opening_hours: dict | None) -> str:
    """Format opening hours."""
    if not opening_hours:
        return ""
    # Opening hours is typically a dict with day names as keys
    # For simplicity, just check if there's any value
    if isinstance(opening_hours, dict):
        # Try to get a representative value
        for _day, hours in opening_hours.items():
            if hours and isinstance(hours, str):
                return hours
    return ""


def _build_facility_context(gym_data: dict) -> str:
    """Build context string from gym data for LLM prompt."""
    parts = []

    # Basic info - location
    pref = gym_data.get("pref", "")
    city = gym_data.get("city", "")
    if pref and city:
        parts.append(f"所在地: {pref}{city}")

    # Categories/facilities
    categories = gym_data.get("categories", [])
    if categories:
        parts.append(f"施設種別: {_format_categories(categories)}")

    # Pool info
    pools = gym_data.get("pools", [])
    pool_info = _format_pools(pools)
    if pool_info:
        parts.append(f"プール: {pool_info}")

    # Court info
    courts = gym_data.get("courts", [])
    court_info = _format_courts(courts)
    if court_info:
        parts.append(f"コート: {court_info}")

    # Hall info
    hall_sports = gym_data.get("hall_sports", [])
    if hall_sports:
        parts.append(f"体育館対応スポーツ: {', '.join(hall_sports)}")
    hall_area = gym_data.get("hall_area_sqm")
    if hall_area:
        parts.append(f"体育館面積: {hall_area}平方メートル")

    # Opening hours
    opening_hours = gym_data.get("opening_hours")
    hours_str = _format_opening_hours(opening_hours)
    if hours_str:
        parts.append(f"営業時間: {hours_str}")

    # Equipments
    equipments = gym_data.get("equipments", [])
    if equipments:
        equip_list = ", ".join(equipments[:10])  # Limit to first 10
        parts.append(f"主な設備: {equip_list}")

    return "\n".join(parts)


async def generate_gym_description(
    gym_data: dict,
    max_length: int = 200,
) -> str:
    """Generate a natural language description for a gym/facility.

    Args:
        gym_data: Dictionary containing gym data (name, categories, pools, etc.)
        max_length: Maximum character length for the description

    Returns:
        Generated description string

    Raises:
        ValueError: If required data is missing
        Exception: If LLM API call fails
    """
    name = gym_data.get("name", "")
    if not name:
        raise ValueError("Gym name is required")

    context = _build_facility_context(gym_data)

    prompt = f"""以下の公営スポーツ施設の紹介文を、{max_length}文字以内で作成してください。

施設名: {name}

施設情報:
{context}

要件:
- 自然な日本語で、SEOに効果的な紹介文を作成
- 施設の特徴や利用メリットを簡潔に伝える
- 「です・ます」調で書く
- 施設名を文頭に含める
- 主な設備や特徴を具体的に紹介する

紹介文:"""

    system_message = (
        "あなたは公営スポーツ施設の紹介文を作成するライターです。"
        "SEOに効果的で読みやすい紹介文を書きます。"
    )

    try:
        client = OpenAIClientWrapper()
        response = await client.chat_completion(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        # Trim to max length if needed
        description = content.strip()
        if len(description) > max_length:
            # Try to cut at sentence boundary
            cut_point = description[:max_length].rfind("。")
            if cut_point > 0:
                description = description[: cut_point + 1]
            else:
                description = description[:max_length]

        logger.info(
            "description_generated",
            gym_name=name,
            description_length=len(description),
        )

        return description

    except Exception as e:
        logger.error(
            "description_generation_failed",
            gym_name=name,
            error=str(e),
        )
        raise
