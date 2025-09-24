import { useEffect } from "react";
import { render, waitFor } from "@testing-library/react";
import { vi, type MockedFunction } from "vitest";

import { AuthProvider, useAuth } from "@/auth/AuthProvider";
import { authClient } from "@/auth/authClient";
import {
  getFavorites as apiGetFavorites,
  addFavorite as apiAddFavorite,
  getHistory as apiGetHistory,
  addHistory as apiAddHistory,
} from "@/lib/apiClient";
import { favoritesStore, resetFavoritesStoreForTests } from "@/store/favoritesStore";
import { historyStore, resetHistoryStoreForTests } from "@/store/historyStore";
import type { GymSummary } from "@/types/gym";

vi.mock("@/auth/authClient", () => {
  const signIn = vi.fn();
  const getSession = vi.fn();
  const signOut = vi.fn();
  const getToken = vi.fn();
  return {
    authClient: {
      mode: "stub" as const,
      signIn,
      getSession,
      signOut,
      getToken,
    },
    authMode: "stub" as const,
  };
});

vi.mock("@/lib/apiClient", () => ({
  getFavorites: vi.fn(),
  addFavorite: vi.fn(),
  removeFavorite: vi.fn(),
  getHistory: vi.fn(),
  addHistory: vi.fn(),
}));

const mockedAuthClient = authClient as {
  mode: "stub";
  signIn: ReturnType<typeof vi.fn>;
  getSession: ReturnType<typeof vi.fn>;
  signOut: ReturnType<typeof vi.fn>;
  getToken: ReturnType<typeof vi.fn>;
};

const mockedGetFavorites = apiGetFavorites as MockedFunction<typeof apiGetFavorites>;
const mockedAddFavorite = apiAddFavorite as MockedFunction<typeof apiAddFavorite>;
const mockedGetHistory = apiGetHistory as MockedFunction<typeof apiGetHistory>;
const mockedAddHistory = apiAddHistory as MockedFunction<typeof apiAddHistory>;

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

const SignInOnMount = () => {
  const { status, signIn } = useAuth();

  useEffect(() => {
    if (status === "unauthenticated") {
      void signIn({ nickname: "tester" });
    }
  }, [signIn, status]);

  return null;
};

describe("AuthProvider store sync", () => {
  beforeEach(() => {
    resetFavoritesStoreForTests();
    resetHistoryStoreForTests();
    window.localStorage.clear();
    vi.clearAllMocks();
    mockedGetFavorites.mockReset();
    mockedAddFavorite.mockReset();
    mockedGetHistory.mockReset();
    mockedAddHistory.mockReset();

    mockedAuthClient.getSession.mockResolvedValue(null);
    mockedAuthClient.signIn.mockResolvedValue({
      token: "token-1",
      user: { id: "user-1", name: "Tester" },
    });
  });

  it("merges local favorites and history on sign-in", async () => {
    const localFavorite = createSummary(1, "Local Favorite");
    const serverFavorite = createSummary(2, "Server Favorite");
    const localHistoryA = createSummary(3, "Local History A");
    const localHistoryB = createSummary(4, "Local History B");
    const serverHistory = createSummary(5, "Server History");

    window.localStorage.setItem("GED_FAVORITES", JSON.stringify([localFavorite]));
    window.localStorage.setItem("GED_HISTORY", JSON.stringify([localHistoryA, localHistoryB]));

    mockedGetFavorites
      .mockResolvedValueOnce([
        {
          gym_id: serverFavorite.id,
          slug: serverFavorite.slug,
          name: serverFavorite.name,
          pref: serverFavorite.prefecture,
          city: serverFavorite.city,
          last_verified_at: serverFavorite.lastVerifiedAt,
        },
      ])
      .mockResolvedValueOnce([
        {
          gym_id: serverFavorite.id,
          slug: serverFavorite.slug,
          name: serverFavorite.name,
          pref: serverFavorite.prefecture,
          city: serverFavorite.city,
          last_verified_at: serverFavorite.lastVerifiedAt,
        },
        {
          gym_id: localFavorite.id,
          slug: localFavorite.slug,
          name: localFavorite.name,
          pref: localFavorite.prefecture,
          city: localFavorite.city,
          last_verified_at: localFavorite.lastVerifiedAt,
        },
      ]);
    mockedAddFavorite.mockResolvedValue(undefined);

    mockedGetHistory
      .mockResolvedValueOnce({ items: [serverHistory] })
      .mockResolvedValueOnce({ items: [serverHistory, localHistoryA, localHistoryB] });
    mockedAddHistory.mockResolvedValue(undefined);

    render(
      <AuthProvider>
        <SignInOnMount />
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(mockedAddFavorite).toHaveBeenCalledWith(expect.any(String), localFavorite.id),
    );
    await waitFor(() =>
      expect(mockedAddHistory).toHaveBeenCalledWith({
        gymIds: [localHistoryA.id, localHistoryB.id],
      }),
    );

    await waitFor(() =>
      expect(favoritesStore.getState().favorites.map(favorite => favorite.gym.id)).toEqual([
        serverFavorite.id,
        localFavorite.id,
      ]),
    );

    await waitFor(() =>
      expect(historyStore.getState().items.map(item => item.id)).toEqual([
        serverHistory.id,
        localHistoryA.id,
        localHistoryB.id,
      ]),
    );

    const storedFavorites = JSON.parse(window.localStorage.getItem("GED_FAVORITES") ?? "[]");
    expect(storedFavorites.map((entry: { id: number }) => entry.id)).toEqual([
      serverFavorite.id,
      localFavorite.id,
    ]);

    const storedHistory = JSON.parse(window.localStorage.getItem("GED_HISTORY") ?? "[]");
    expect(storedHistory.map((entry: { id: number }) => entry.id)).toEqual([
      serverHistory.id,
      localHistoryA.id,
      localHistoryB.id,
    ]);
  });
});
