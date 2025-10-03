import { describe, expect, test, beforeEach, afterAll } from "vitest";

import { filterOutDummyGyms } from "@/lib/filters";

const ORIGINAL_ENV = { ...process.env };

beforeEach(() => {
  process.env = { ...ORIGINAL_ENV };
});

afterAll(() => {
  process.env = ORIGINAL_ENV;
});

type TestGym = {
  slug?: string | null;
  name?: string | null;
};

const buildGyms = (): TestGym[] => [
  { slug: "dummy-123", name: "ダミージム" },
  { slug: "bulk-456", name: "まとめ登録" },
  { slug: "regular", name: "通常ジム" },
  { slug: "other", name: "ダミー以外" },
];

describe("filterOutDummyGyms", () => {
  test("dev/demo 環境ではダミーデータを除外する", () => {
    process.env.NEXT_PUBLIC_APP_ENV = "demo";

    const result = filterOutDummyGyms(buildGyms());

    expect(result).toEqual([
      { slug: "regular", name: "通常ジム" },
      { slug: "other", name: "ダミー以外" },
    ]);
  });

  test("prod 環境では除外しない", () => {
    process.env.NEXT_PUBLIC_APP_ENV = "prod";

    const gyms = buildGyms();
    const result = filterOutDummyGyms(gyms);

    expect(result).toBe(gyms);
  });

  test("NEXT_PUBLIC_APP_ENV 未設定時は NODE_ENV が production 以外なら除外する", () => {
    delete process.env.NEXT_PUBLIC_APP_ENV;
    process.env.NODE_ENV = "development";

    const result = filterOutDummyGyms(buildGyms());

    expect(result).toHaveLength(2);
  });

  test("NEXT_PUBLIC_APP_ENV 未設定時は NODE_ENV=production なら除外しない", () => {
    delete process.env.NEXT_PUBLIC_APP_ENV;
    process.env.NODE_ENV = "production";

    const gyms = buildGyms();
    const result = filterOutDummyGyms(gyms);

    expect(result).toBe(gyms);
  });
});
