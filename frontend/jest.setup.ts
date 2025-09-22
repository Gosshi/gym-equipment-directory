import { afterEach, jest } from "@jest/globals";
import "@testing-library/jest-dom";

const defaultApiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
process.env.NEXT_PUBLIC_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? defaultApiBase;
process.env.NEXT_PUBLIC_API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? defaultApiBase;

afterEach(() => {
  jest.clearAllMocks();
});
