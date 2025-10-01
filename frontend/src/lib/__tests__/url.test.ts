import { describe, expect, it } from "vitest";

import { encodeOnce } from "@/lib/url";

describe("encodeOnce", () => {
  it("encodes plain slugs containing multibyte characters", () => {
    const slug = "有明ジム";
    expect(encodeOnce(slug)).toBe(encodeURIComponent(slug));
  });

  it("returns already encoded slugs as-is", () => {
    const encoded = encodeURIComponent("江東区-ジム");
    expect(encodeOnce(encoded)).toBe(encoded);
  });

  it("encodes strings with spaces only once", () => {
    const slug = "tokyo gym";
    expect(encodeOnce(slug)).toBe("tokyo%20gym");
  });

  it("encodes strings with invalid escape sequences", () => {
    const invalid = "%E0%A4%A";
    expect(encodeOnce(invalid)).toBe(encodeURIComponent(invalid));
  });
});
