"""Geospatial utility helpers used by tests and services."""

from __future__ import annotations

import math

LatLng = tuple[float, float]


def haversine_distance_km(point_a: LatLng, point_b: LatLng, *, radius_km: float = 6371.0) -> float:
    """Compute the great-circle distance between two points in kilometres.

    The implementation mirrors the SQL expressions used in the API layer and clamps the
    intermediate value to avoid floating point drift near the poles.
    """

    lat1, lng1 = point_a
    lat2, lng2 = point_b

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lng2 - lng1)

    sin_dphi = math.sin(dphi / 2.0)
    sin_dlambda = math.sin(dlambda / 2.0)

    a = sin_dphi**2 + math.cos(phi1) * math.cos(phi2) * sin_dlambda**2
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.asin(math.sqrt(a))
    return radius_km * c


__all__ = ["LatLng", "haversine_distance_km"]
