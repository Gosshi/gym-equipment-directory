import { apiFetch } from "@/lib/apiClient";

export interface HealthResponse {
  status: "ok" | "error";
  details?: Record<string, unknown>;
}

export async function fetchHealth() {
  return apiFetch<HealthResponse>("/health", { timeoutMs: 5000 });
}
