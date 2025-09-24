export type LatLng = {
  lat: number;
  lng: number;
};

const withinRange = (value: number, min: number, max: number) => value >= min && value <= max;

export const isLatLng = (value: unknown): value is LatLng => {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  return typeof record.lat === "number" && typeof record.lng === "number";
};

export const normalizeLatLng = (lat: number, lng: number): LatLng | null => {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return null;
  }

  const normalizedLat = Number.parseFloat(lat.toFixed(6));
  const normalizedLng = Number.parseFloat(lng.toFixed(6));

  if (!withinRange(normalizedLat, -90, 90) || !withinRange(normalizedLng, -180, 180)) {
    return null;
  }

  return { lat: normalizedLat, lng: normalizedLng };
};

export const parseLatLng = (text: string): LatLng | null => {
  const trimmed = text.trim();
  if (!trimmed) {
    return null;
  }

  const parts = trimmed
    .split(/[\s,]+/)
    .map(part => part.trim())
    .filter(Boolean);

  if (parts.length !== 2) {
    return null;
  }

  const [latRaw, lngRaw] = parts;
  const lat = Number.parseFloat(latRaw);
  const lng = Number.parseFloat(lngRaw);

  return normalizeLatLng(lat, lng);
};

const DEG_TO_RAD = Math.PI / 180;
const EARTH_RADIUS_KM = 6371;

export const haversineDistanceKm = (from: LatLng, to: LatLng): number => {
  const fromLatRad = from.lat * DEG_TO_RAD;
  const toLatRad = to.lat * DEG_TO_RAD;
  const deltaLat = (to.lat - from.lat) * DEG_TO_RAD;
  const deltaLng = (to.lng - from.lng) * DEG_TO_RAD;

  const sinLat = Math.sin(deltaLat / 2);
  const sinLng = Math.sin(deltaLng / 2);

  const a = sinLat * sinLat + Math.cos(fromLatRad) * Math.cos(toLatRad) * sinLng * sinLng;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return Number.parseFloat((EARTH_RADIUS_KM * c).toFixed(3));
};

export const formatLatLng = (value: LatLng, precision = 6) => {
  const decimals = Math.max(0, Math.min(precision, 8));
  return `${value.lat.toFixed(decimals)},${value.lng.toFixed(decimals)}`;
};

export const metersToKilometres = (meters: number) => Number.parseFloat((meters / 1000).toFixed(3));

export const kilometresToMeters = (kilometres: number) => Math.round(kilometres * 1000);
