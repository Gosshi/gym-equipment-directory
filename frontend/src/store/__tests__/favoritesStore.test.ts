import { act, waitFor } from "@testing-library/react";

import { getFavorites as apiGetFavorites, addFavorite as apiAddFavorite } from "@/lib/apiClient";
import { favoritesStore, resetFavoritesStoreForTests } from "@/store/favoritesStore";
import type { GymSummary } from "@/types/gym";

jest.mock("@/lib/apiClient", () => ({
  getFavorites: jest.fn(),
  addFavorite: jest.fn(),
  removeFavorite: jest.fn(),
}));

const mockedGetFavorites = apiGetFavorites as jest.MockedFunction<typeof apiGetFavorites>;
const mockedAddFavorite = apiAddFavorite as jest.MockedFunction<typeof apiAddFavorite>;

const createSummary = (id: number, name: string): GymSummary => ({
  id,
  slug: `gym-${id}`,
  name,
  prefecture: "tokyo",
  city: "chiyoda",
  address: "東京都千代田区1-1",
  thumbnailUrl: null,
  lastVerifiedAt: null,
});

describe("favoritesStore", () => {
  beforeEach(() => {
    resetFavoritesStoreForTests();
    window.localStorage.clear();
    // 安定した device_id を固定 (ensureDeviceId 内で利用される)
    window.localStorage.setItem("GED_DEVICE_ID", "test-device-1");
    jest.clearAllMocks();
    mockedGetFavorites.mockReset();
    mockedAddFavorite.mockReset();
  });

  it("initializes from localStorage", async () => {
    window.localStorage.setItem(
      "GED_FAVORITES",
      JSON.stringify([createSummary(1, "Gym A"), createSummary(2, "Gym B")]),
    );

    await act(async () => {
      await favoritesStore.getState().initialize();
    });

    expect(favoritesStore.getState().favorites).toHaveLength(2);
    expect(favoritesStore.getState().favorites[0].gym.name).toBe("Gym A");
  });

  it("adds a favorite locally when unauthenticated", async () => {
    const summary = createSummary(10, "Local Gym");

    await act(async () => {
      favoritesStore.getState().setAuthenticated(false);
      await favoritesStore.getState().addFavorite(summary);
    });

    const state = favoritesStore.getState();
    expect(state.favorites.map((favorite) => favorite.gym.id)).toEqual([summary.id]);
    expect(state.pendingIds).toHaveLength(0);
    expect(mockedAddFavorite).not.toHaveBeenCalled();

    const stored = JSON.parse(window.localStorage.getItem("GED_FAVORITES") ?? "[]");
    expect(stored).toHaveLength(1);
    expect(stored[0].id).toBe(summary.id);
  });

  it("adds a favorite through the API when authenticated", async () => {
    const summary = createSummary(20, "Remote Gym");
    mockedAddFavorite.mockResolvedValue(undefined);
    // サーバー FavoriteItem 形状 (snake_case)
    mockedGetFavorites.mockResolvedValue([
      {
        gym_id: summary.id,
        slug: summary.slug,
        name: summary.name,
        pref: summary.prefecture,
        city: summary.city,
        last_verified_at: summary.lastVerifiedAt,
      },
    ]);

    await act(async () => {
      favoritesStore.getState().setAuthenticated(true);
      await favoritesStore.getState().addFavorite(summary);
    });

  expect(mockedAddFavorite).toHaveBeenCalledWith("test-device-1", summary.id);
    await waitFor(() =>
      expect(favoritesStore.getState().favorites[0]?.gym.id).toBe(summary.id),
    );
  });

  it("merges local favorites into the server on sync", async () => {
    const localA = createSummary(1, "Local A");
    const localB = createSummary(2, "Local B");

    window.localStorage.setItem("GED_FAVORITES", JSON.stringify([localA, localB]));

    mockedGetFavorites
      .mockResolvedValueOnce([
        {
          gym_id: localA.id,
          slug: localA.slug,
          name: localA.name,
          pref: localA.prefecture,
          city: localA.city,
          last_verified_at: localA.lastVerifiedAt,
        },
      ])
      .mockResolvedValueOnce([
        {
          gym_id: localA.id,
          slug: localA.slug,
          name: localA.name,
          pref: localA.prefecture,
          city: localA.city,
          last_verified_at: localA.lastVerifiedAt,
        },
        {
          gym_id: localB.id,
          slug: localB.slug,
          name: localB.name,
          pref: localB.prefecture,
          city: localB.city,
          last_verified_at: localB.lastVerifiedAt,
        },
      ]);
    mockedAddFavorite.mockResolvedValue(undefined);

    await act(async () => {
      favoritesStore.getState().setAuthenticated(true);
      await favoritesStore.getState().syncWithServer("user-1");
    });

  expect(mockedAddFavorite).toHaveBeenCalledWith("test-device-1", localB.id);
    expect(favoritesStore.getState().favorites.map((favorite) => favorite.gym.id)).toEqual([
      localA.id,
      localB.id,
    ]);

    const stored = JSON.parse(window.localStorage.getItem("GED_FAVORITES") ?? "[]");
    expect(stored.map((entry: { id: number }) => entry.id)).toEqual([localA.id, localB.id]);
  });
});
