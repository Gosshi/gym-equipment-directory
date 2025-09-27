import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSelectedGym } from "../useSelectedGym";
import { resetMapSelectionStoreForTests } from "@/state/mapSelection";
import type { NearbyGym } from "@/types/gym";

const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
};

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  usePathname: () => "/gyms/nearby",
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

const buildGym = (id: number, slug: string): NearbyGym => ({
  id,
  slug,
  name: slug,
  prefecture: "tokyo",
  city: "chiyoda",
  latitude: 35.0 + id,
  longitude: 139.0 + id,
  distanceKm: 1,
  lastVerifiedAt: null,
});

const syncHistoryWithLastCall = (calls: unknown[][]) => {
  const lastCall = calls[calls.length - 1];
  if (!lastCall) {
    return;
  }
  const [url] = lastCall as [string];
  const target = new URL(url, "http://localhost");
  window.history.replaceState(null, "", target.toString());
};

describe("useSelectedGym history behaviour", () => {
  beforeEach(() => {
    resetMapSelectionStoreForTests();
    window.history.replaceState(null, "", "http://localhost/gyms/nearby");
    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();
  });

  it("pushes history entries when selecting gyms", async () => {
    const gyms = [buildGym(101, "alpha"), buildGym(102, "beta")];
    const { result, unmount } = renderHook(props => useSelectedGym(props), {
      initialProps: { gyms, requiredGymIds: gyms.map(gym => gym.id) },
    });

    act(() => {
      result.current.selectGym(101, "list");
    });

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledTimes(1);
    });
    const [url] = mockRouter.push.mock.calls[0] as [string];
    expect(url).toContain("gym=101");
    expect(result.current.selectedGymId).toBe(101);
    syncHistoryWithLastCall(mockRouter.push.mock.calls);

    unmount();
  });

  it("replaces history when the selected gym disappears", async () => {
    const gyms = [buildGym(201, "gamma"), buildGym(202, "delta")];
    const { result, rerender, unmount } = renderHook(props => useSelectedGym(props), {
      initialProps: { gyms, requiredGymIds: gyms.map(gym => gym.id) },
    });

    act(() => {
      result.current.selectGym(201, "list");
    });

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledTimes(1);
    });
    syncHistoryWithLastCall(mockRouter.push.mock.calls);
    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();

    const nextGyms = [buildGym(202, "delta")];
    rerender({ gyms: nextGyms, requiredGymIds: nextGyms.map(gym => gym.id) });

    await waitFor(() => {
      expect(mockRouter.replace).toHaveBeenCalledTimes(1);
    });
    const [url] = mockRouter.replace.mock.calls[0] as [string];
    expect(url).not.toContain("gym=201");
    expect(result.current.selectedGymId).toBeNull();

    unmount();
  });
});
