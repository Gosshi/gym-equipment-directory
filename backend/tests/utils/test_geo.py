import pytest

from app.utils.geo import haversine_distance_km


@pytest.mark.parametrize(
    "point_a, point_b, expected",
    [
        ((35.0, 135.0), (35.0, 135.0), 0.0),
        ((35.681236, 139.767125), (35.690921, 139.700258), 6.13),
        ((35.681236, 139.767125), (40.712776, -74.005974), 10848.0),
    ],
)
def test_haversine_distance(point_a, point_b, expected):
    distance = haversine_distance_km(point_a, point_b)
    assert distance == pytest.approx(expected, rel=0.02)


def test_haversine_near_poles_stability():
    north = (89.9, 0.0)
    south = (89.9, 180.0)
    distance = haversine_distance_km(north, south)
    assert distance == pytest.approx(22.24, rel=0.02)


def test_haversine_antimeridian():
    west = (0.0, 179.9)
    east = (0.0, -179.9)
    distance = haversine_distance_km(west, east)
    assert distance == pytest.approx(22.24, rel=0.02)
