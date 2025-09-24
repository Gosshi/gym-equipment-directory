import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom";

const defaultApiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
process.env.NEXT_PUBLIC_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? defaultApiBase;
process.env.NEXT_PUBLIC_API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? defaultApiBase;
process.env.NEXT_PUBLIC_AUTH_MODE = process.env.NEXT_PUBLIC_AUTH_MODE ?? "stub";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
