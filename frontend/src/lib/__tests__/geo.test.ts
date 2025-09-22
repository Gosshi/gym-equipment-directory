import {
  formatLatLng,
  haversineDistanceKm,
  kilometresToMeters,
  metersToKilometres,
  normalizeLatLng,
  parseLatLng,
} from "@/lib/geo";

describe("geo utilities", () => {
  it("normalises coordinates within the valid range", () => {
    expect(normalizeLatLng(35.6895, 139.6917)).toEqual({ lat: 35.6895, lng: 139.6917 });
  });

  it("returns null when coordinates are outside the valid range", () => {
    expect(normalizeLatLng(95, 10)).toBeNull();
    expect(normalizeLatLng(10, 200)).toBeNull();
  });

  it("parses latitude and longitude strings", () => {
    expect(parseLatLng("35.681236,139.767125")).toEqual({
      lat: 35.681236,
      lng: 139.767125,
    });
    expect(parseLatLng("35.681236 139.767125")).toEqual({
      lat: 35.681236,
      lng: 139.767125,
    });
    expect(parseLatLng("invalid")).toBeNull();
  });

  it("returns null for malformed coordinate strings", () => {
    expect(parseLatLng("35.0")).toBeNull();
    expect(parseLatLng("")).toBeNull();
  });

  it("calculates haversine distance in kilometres", () => {
    const tokyoStation = { lat: 35.681236, lng: 139.767125 };
    const shinjukuStation = { lat: 35.690921, lng: 139.700258 };

    expect(haversineDistanceKm(tokyoStation, shinjukuStation)).toBeCloseTo(6.13, 2);
  });

  it("formats coordinates with precision", () => {
    expect(formatLatLng({ lat: 35.681236, lng: 139.767125 }, 4)).toBe("35.6812,139.7671");
  });

  it("converts between metres and kilometres", () => {
    expect(metersToKilometres(3200)).toBeCloseTo(3.2);
    expect(kilometresToMeters(3.2)).toBe(3200);
  });
});
