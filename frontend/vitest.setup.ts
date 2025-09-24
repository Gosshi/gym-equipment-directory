import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom";
import { server } from "./tests/msw/server";

const defaultApiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
process.env.NEXT_PUBLIC_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? defaultApiBase;
process.env.NEXT_PUBLIC_API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? defaultApiBase;
process.env.NEXT_PUBLIC_AUTH_MODE = process.env.NEXT_PUBLIC_AUTH_MODE ?? "stub";

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});

afterEach(() => {
  server.resetHandlers();
  cleanup();
  vi.clearAllMocks();
});

afterAll(() => {
  server.close();
});

if (!HTMLElement.prototype.scrollIntoView) {
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
    configurable: true,
    value: vi.fn(),
  });
}
