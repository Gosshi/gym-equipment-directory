import { describe, expect, it } from "vitest";

import {
  clearSelectedFromSearchParams,
  getSelectedFromSearchParams,
  isSelectedMatching,
  setSelectedOnSearchParams,
} from "@/lib/urlState";

describe("urlState", () => {
  describe("getSelectedFromSearchParams", () => {
    it("returns null when the parameter is absent", () => {
      expect(getSelectedFromSearchParams(new URLSearchParams("q=test"))).toBeNull();
    });

    it("returns null when the value contains invalid characters", () => {
      const params = new URLSearchParams("selected=bad%20slug");
      expect(getSelectedFromSearchParams(params)).toBeNull();
    });

    it("returns the sanitized slug when present", () => {
      const params = new URLSearchParams("selected=gym-123");
      expect(getSelectedFromSearchParams(params)).toBe("gym-123");
    });
  });

  describe("setSelectedOnSearchParams", () => {
    it("sets the selected parameter when valid", () => {
      const params = new URLSearchParams("q=test");
      const result = setSelectedOnSearchParams(params, "gym-42");
      expect(result).toBe("q=test&selected=gym-42");
    });

    it("removes the parameter when value is null", () => {
      const params = new URLSearchParams("selected=gym-42");
      const result = setSelectedOnSearchParams(params, null);
      expect(result).toBe("");
    });

    it("ignores invalid values", () => {
      const params = new URLSearchParams("selected=gym-42");
      const result = setSelectedOnSearchParams(params, "invalid slug");
      expect(result).toBe("selected=gym-42");
    });
  });

  describe("clearSelectedFromSearchParams", () => {
    it("removes the selected parameter", () => {
      const params = new URLSearchParams("selected=gym-42&page=2");
      const result = clearSelectedFromSearchParams(params);
      expect(result).toBe("page=2");
    });
  });

  describe("isSelectedMatching", () => {
    it("returns true when both values are null", () => {
      expect(isSelectedMatching(null, null)).toBe(true);
    });

    it("returns false when only candidate exists", () => {
      expect(isSelectedMatching("gym-1", null)).toBe(false);
    });

    it("returns false for mismatched values", () => {
      expect(isSelectedMatching("gym-1", "gym-2")).toBe(false);
    });

    it("returns true for matching sanitized values", () => {
      expect(isSelectedMatching("gym-2", "gym-2")).toBe(true);
    });
  });
});
