from datetime import datetime
from types import SimpleNamespace

from app.dto.mappers import (
    assemble_gym_detail,
    map_equipment_master,
    map_gym_to_summary,
)


def test_map_gym_to_summary_converts_timestamp_to_iso() -> None:
    gym = SimpleNamespace(id=1, slug="test-gym", name="Test Gym", pref="chiba", city="funabashi")
    dt = datetime(2024, 1, 2, 3, 4, 5)

    dto = map_gym_to_summary(
        gym,
        last_verified_at=dt,
        score=1.2,
        freshness_score=0.8,
        richness_score=0.7,
    )

    assert dto.slug == "test-gym"
    assert dto.last_verified_at == dt.isoformat()
    assert dto.score == 1.2
    assert dto.freshness_score == 0.8
    assert dto.richness_score == 0.7


def test_assemble_gym_detail_builds_nested_dtos() -> None:
    gym = SimpleNamespace(
        id=10,
        slug="detail-gym",
        name="Detail Gym",
        city="tokyo",
        pref="tokyo",
    )
    detail = assemble_gym_detail(
        gym,
        equipments=[{"equipment_slug": "rack", "equipment_name": "Rack"}],
        equipment_summaries=[
            {
                "slug": "rack",
                "name": "Rack",
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


def test_map_equipment_master_from_mapping() -> None:
    mapping = {"id": 3, "slug": "bike", "name": "Bike", "category": "cardio"}

    dto = map_equipment_master(mapping)

    assert dto.slug == "bike"
    assert dto.category == "cardio"
