import {
  DEFAULT_QUERY_STATE,
  areCategoriesEqual,
  normalizeCategories,
  parseSearchParams,
  serializeSearchParams,
  type GymSearchFilters,
} from "@/lib/searchParams";

describe("searchParams", () => {
  it("parses URLSearchParams into a normalized filter object", () => {
    const params = new URLSearchParams(
      "q=bench&pref=tokyo&city=shinjuku&cats=squat-rack,dumbbell&sort=created_at&page=2&limit=30",
    );

    const filters = parseSearchParams(params);

    expect(filters).toEqual<GymSearchFilters>({
      q: "bench",
      pref: "tokyo",
      city: "shinjuku",
      cats: ["squat-rack", "dumbbell"],
      sort: "created_at",
      page: 2,
      limit: 30,
    });
  });

  it("falls back to defaults when invalid values are provided", () => {
    const params = new URLSearchParams(
      "sort=unknown&page=-5&limit=999&cats=, ,bench,,bench",
    );

    const filters = parseSearchParams(params);

    expect(filters.sort).toBe(DEFAULT_QUERY_STATE.sort);
    expect(filters.page).toBe(DEFAULT_QUERY_STATE.page);
    expect(filters.limit).toBe(50);
    expect(filters.cats).toEqual(["bench"]);
  });

  it("serializes filters back into URLSearchParams while omitting defaults", () => {
    const filters: GymSearchFilters = {
      q: "bench",
      pref: null,
      city: null,
      cats: [],
      sort: DEFAULT_QUERY_STATE.sort,
      page: 1,
      limit: DEFAULT_QUERY_STATE.limit,
    };

    const params = serializeSearchParams(filters);

    expect(params.toString()).toBe("q=bench");
  });

  it("round-trips through parse and serialize without losing information", () => {
    const original: GymSearchFilters = {
      q: "deadlift",
      pref: "osaka",
      city: "sakai",
      cats: ["platform", "chalk-station"],
      sort: "freshness",
      page: 3,
      limit: 40,
    };

    const params = serializeSearchParams(original);
    const parsed = parseSearchParams(params);

    expect(parsed).toEqual(original);
  });

  it("normalizes category arrays and allows equality comparison", () => {
    const values = [" Bench ", "bench", "Squat"];
    const normalized = normalizeCategories(values);

    expect(normalized).toEqual(["Bench", "Squat"]);
    expect(areCategoriesEqual(normalized, ["Bench", "Squat"])).toBe(true);
  });
});
