import {
  DEFAULT_DISTANCE_KM,
  DEFAULT_FILTER_STATE,
  DEFAULT_LIMIT,
  DEFAULT_SORT,
  MAX_DISTANCE_KM,
  MAX_LIMIT,
  SORT_OPTIONS,
  parseFilterState,
  serializeFilterState,
} from "@/lib/searchParams";

describe("searchParams", () => {
  it("parses query parameters into a normalized filter state", () => {
    const params = new URLSearchParams(
      "q= bench &pref=tokyo&city= shinjuku &cats=squat-rack,barbell,squat-rack&sort=freshness&page=2&per_page=40&distance=25&lat=35.681&lng=139.767",
    );

    const state = parseFilterState(params);

    expect(state).toEqual({
      q: "bench",
      pref: "tokyo",
      city: "shinjuku",
      categories: ["squat-rack", "barbell"],
      sort: "fresh",
      page: 2,
      limit: 40,
      distance: 25,
      lat: 35.681,
      lng: 139.767,
    });
  });

  it("falls back to defaults when parameters are missing or invalid", () => {
    const params = new URLSearchParams("cats=,,,&page=-3&limit=9999&distance=999");

    const state = parseFilterState(params);

    expect(state.q).toBe("");
    expect(state.pref).toBeNull();
    expect(state.city).toBeNull();
    expect(state.categories).toEqual([]);
    expect(state.sort).toBe(DEFAULT_SORT);
    expect(state.page).toBe(1);
    expect(state.limit).toBe(MAX_LIMIT);
    expect(state.distance).toBe(MAX_DISTANCE_KM);
    expect(state.lat).toBeNull();
    expect(state.lng).toBeNull();
  });

  it("serializes a filter state into query parameters while omitting defaults", () => {
    const params = serializeFilterState({
      ...DEFAULT_FILTER_STATE,
      q: "deadlift",
      pref: "osaka",
      city: "osaka-city",
      categories: ["dumbbell", "smith-machine"],
      sort: "newest",
      page: 3,
      limit: 30,
      distance: DEFAULT_DISTANCE_KM + 1,
      lat: 35.01,
      lng: 135.75,
    });

    expect(params.get("q")).toBe("deadlift");
    expect(params.get("pref")).toBe("osaka");
    expect(params.get("city")).toBe("osaka-city");
    expect(params.get("cats")).toBe("dumbbell,smith-machine");
    expect(params.get("sort")).toBe("newest");
    expect(params.get("page")).toBe("3");
    expect(params.get("per_page")).toBe("30");
    expect(params.get("distance")).toBe(String(DEFAULT_DISTANCE_KM + 1));
    expect(params.get("lat")).toBe("35.010000");
    expect(params.get("lng")).toBe("135.750000");
  });

  it("round-trips between serialization and parsing", () => {
    const params = serializeFilterState({
      q: "squat",
      pref: "hokkaido",
      city: "sapporo",
      categories: ["power-rack"],
      sort: "popular",
      page: 4,
      limit: 24,
      distance: 12,
      lat: 43.0621,
      lng: 141.3544,
    });

    const state = parseFilterState(params);

    expect(state).toEqual({
      q: "squat",
      pref: "hokkaido",
      city: "sapporo",
      categories: ["power-rack"],
      sort: "popular",
      page: 4,
      limit: 24,
      distance: 12,
      lat: 43.0621,
      lng: 141.3544,
    });
  });

  it("recognizes the available sort options", () => {
    const params = new URLSearchParams();
    for (const option of SORT_OPTIONS) {
      params.set("sort", option);
      expect(parseFilterState(params).sort).toBe(option);
    }
  });

  it("understands legacy parameter names for compatibility", () => {
    const params = new URLSearchParams(
      "prefecture=kanagawa&equipments=cable-machine&per_page=10",
    );

    const state = parseFilterState(params);

    expect(state.pref).toBe("kanagawa");
    expect(state.categories).toEqual(["cable-machine"]);
    expect(state.limit).toBe(10);
  });
});
