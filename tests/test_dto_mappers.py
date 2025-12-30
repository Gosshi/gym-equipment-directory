from datetime import datetime
from types import SimpleNamespace

from app.dto.mappers import (
    assemble_gym_detail,
    map_equipment_master,
    map_gym_to_summary,
)


def test_map_gym_to_summary_converts_timestamp_to_iso() -> None:
    gym = SimpleNamespace(
        id=1,
        slug="test-gym",
        name="Test Gym",
        pref="chiba",
        city="funabashi",
        official_url="https://example.com/test-gym",
    )
    dt = datetime(2024, 1, 2, 3, 4, 5)

    dto = map_gym_to_summary(
        gym,
        last_verified_at=dt,
        score=1.2,
        freshness_score=0.8,
        richness_score=0.7,
        distance_km=12.3,
    )

    assert dto.slug == "test-gym"
    assert dto.last_verified_at == dt.isoformat()
    assert dto.score == 1.2
    assert dto.freshness_score == 0.8
    assert dto.richness_score == 0.7
    assert dto.distance_km == 12.3
    assert dto.official_url == "https://example.com/test-gym"


def test_assemble_gym_detail_builds_nested_dtos() -> None:
    gym = SimpleNamespace(
        id=10,
        slug="detail-gym",
        name="Detail Gym",
        city="tokyo",
        pref="tokyo",
        official_url="https://example.com/detail-gym",
    )
    detail = assemble_gym_detail(
        gym,
        equipments=[
            {
                "equipment_slug": "rack",
                "equipment_name": "Rack",
                "category": "strength",
                "count": 2,
                "max_weight_kg": 180,
            }
        ],
        equipment_summaries=[
            {
                "slug": "rack",
                "name": "Rack",
                "category": "strength",
                "count": 2,
                "max_weight_kg": 180,
                "availability": "present",
                "verification_status": "verified",
                "last_verified_at": None,
                "source": None,
            }
        ],
        images=[{"url": "https://example.com/image.jpg", "verified": True, "source": None}],
        updated_at=datetime(2024, 2, 3, 4, 5, 6),
        freshness=0.5,
        richness=0.6,
        score=0.55,
    )

    assert detail.slug == "detail-gym"
    assert detail.images[0].url == "https://example.com/image.jpg"
    assert detail.freshness == 0.5
    assert detail.updated_at == datetime(2024, 2, 3, 4, 5, 6).isoformat()
    assert detail.equipments[0].name == "Rack"
    assert detail.equipments[0].category == "strength"
    assert detail.equipments[0].description == "2台 / 最大180kg"
    assert detail.equipment_details[0].name == "Rack"
    assert detail.official_url == "https://example.com/detail-gym"


def test_map_equipment_master_from_mapping() -> None:
    mapping = {"id": 3, "slug": "bike", "name": "Bike", "category": "cardio"}

    dto = map_equipment_master(mapping)

    assert dto.slug == "bike"
    assert dto.category == "cardio"


def test_map_gym_to_summary_with_category_fallback() -> None:
    # 1. categories column present
    gym1 = SimpleNamespace(
        id=1,
        slug="g1",
        name="G1",
        categories=["pool", "gym"],
        category="gym",
        parsed_json={"meta": {"categories": ["other"], "category": "other"}},
    )
    dto1 = map_gym_to_summary(gym1, last_verified_at=None, score=None)
    assert dto1.categories == ["pool", "gym"]

    # 2. meta.categories present
    gym2 = SimpleNamespace(
        id=2,
        slug="g2",
        name="G2",
        categories=None,
        category="gym",
        parsed_json={"meta": {"categories": ["court", "hall"], "category": "other"}},
    )
    dto2 = map_gym_to_summary(gym2, last_verified_at=None, score=None)
    assert dto2.categories == ["court", "hall"]

    # 3. category column present
    gym3 = SimpleNamespace(
        id=3,
        slug="g3",
        name="G3",
        categories=None,
        category="martial_arts",
        parsed_json={"meta": {"category": "other"}},
    )
    dto3 = map_gym_to_summary(gym3, last_verified_at=None, score=None)
    assert dto3.categories == ["martial_arts"]

    # 4. meta.category present
    gym4 = SimpleNamespace(
        id=4,
        slug="g4",
        name="G4",
        categories=None,
        category=None,
        parsed_json={"meta": {"category": "archery"}},
    )
    dto4 = map_gym_to_summary(gym4, last_verified_at=None, score=None)
    assert dto4.categories == ["archery"]

    # 5. Fallback to empty
    gym5 = SimpleNamespace(
        id=5, slug="g5", name="G5", categories=None, category=None, parsed_json={}
    )
    dto5 = map_gym_to_summary(gym5, last_verified_at=None, score=None)
    assert dto5.categories == []
