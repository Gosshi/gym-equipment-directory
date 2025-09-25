import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { GymList } from "@/components/gyms/GymList";
import type { GymSearchMeta, GymSummary } from "@/types/gym";

const buildMeta = (overrides: Partial<GymSearchMeta> = {}): GymSearchMeta => ({
  total: 0,
  page: 1,
  perPage: 10,
  hasNext: false,
  hasPrev: false,
  hasMore: false,
  pageToken: null,
  ...overrides,
});

const baseProps = {
  gyms: [] as GymSummary[],
  meta: buildMeta(),
  page: 1,
  limit: 10,
  isLoading: false,
  isInitialLoading: false,
  error: null,
  onRetry: vi.fn(),
  onPageChange: vi.fn(),
  onLimitChange: vi.fn(),
};

describe("GymList", () => {
  it("shows empty state messaging when there are no gyms", () => {
    render(<GymList {...baseProps} onClearFilters={vi.fn()} />);

    expect(screen.getByText("該当するジムが見つかりませんでした")).toBeInTheDocument();
  });
});
