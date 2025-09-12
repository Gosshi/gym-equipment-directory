import pytest
from sqlalchemy import select

from app.models import Gym
from app.models.gym_image import GymImage


@pytest.mark.anyio
async def test_gym_detail_includes_images_field(app_client, session):
    # Arrange: ensure target gym exists from seed
    gym = await session.scalar(select(Gym).where(Gym.slug == "dummy-funabashi-east"))
    assert gym is not None

    # No images yet -> should return empty list
    resp = await app_client.get(f"/gyms/{gym.slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert "images" in body
    assert isinstance(body["images"], list)
    assert body["images"] == []

    # Add two images
    session.add_all(
        [
            GymImage(gym_id=gym.id, url="https://ex.com/1.jpg", source="web", verified=False),
            GymImage(gym_id=gym.id, url="https://ex.com/2.jpg", source="web", verified=True),
        ]
    )
    await session.commit()

    # Act
    resp2 = await app_client.get(f"/gyms/{gym.slug}")
    assert resp2.status_code == 200
    data = resp2.json()

    # Assert
    imgs = data.get("images")
    assert isinstance(imgs, list) and len(imgs) == 2
    # Ensure minimal fields
    for it in imgs:
        assert {"url", "source", "verified", "created_at"} <= set(it.keys())
