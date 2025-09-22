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
    mockedGetFavorites.mockResolvedValue({ items: [summary] });

    await act(async () => {
      favoritesStore.getState().setAuthenticated(true);
      await favoritesStore.getState().addFavorite(summary);
    });

    expect(mockedAddFavorite).toHaveBeenCalledWith(summary.id);
    await waitFor(() =>
      expect(favoritesStore.getState().favorites[0]?.gym.id).toBe(summary.id),
    );
  });

  it("merges local favorites into the server on sync", async () => {
    const localA = createSummary(1, "Local A");
    const localB = createSummary(2, "Local B");

    window.localStorage.setItem("GED_FAVORITES", JSON.stringify([localA, localB]));

    mockedGetFavorites
      .mockResolvedValueOnce({ items: [localA] })
      .mockResolvedValueOnce({ items: [localA, localB] });
    mockedAddFavorite.mockResolvedValue(undefined);

    await act(async () => {
      favoritesStore.getState().setAuthenticated(true);
      await favoritesStore.getState().syncWithServer("user-1");
    });

    expect(mockedAddFavorite).toHaveBeenCalledWith(localB.id);
    expect(favoritesStore.getState().favorites.map((favorite) => favorite.gym.id)).toEqual([
      localA.id,
      localB.id,
    ]);

    const stored = JSON.parse(window.localStorage.getItem("GED_FAVORITES") ?? "[]");
    expect(stored.map((entry: { id: number }) => entry.id)).toEqual([localA.id, localB.id]);
  });
});
