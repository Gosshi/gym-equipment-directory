import { useEffect } from "react";
import { render, waitFor } from "@testing-library/react";

import { AuthProvider, useAuth } from "@/auth/AuthProvider";
import {
  getFavorites as apiGetFavorites,
  addFavorite as apiAddFavorite,
  getHistory as apiGetHistory,
  addHistory as apiAddHistory,
} from "@/lib/apiClient";
import { favoritesStore, resetFavoritesStoreForTests } from "@/store/favoritesStore";
import { historyStore, resetHistoryStoreForTests } from "@/store/historyStore";
import type { GymSummary } from "@/types/gym";

jest.mock("@/auth/authClient", () => {
  const signIn = jest.fn();
  const getSession = jest.fn();
  const signOut = jest.fn();
  const getToken = jest.fn();
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

jest.mock("@/lib/apiClient", () => ({
  getFavorites: jest.fn(),
  addFavorite: jest.fn(),
  removeFavorite: jest.fn(),
  getHistory: jest.fn(),
  addHistory: jest.fn(),
}));

const mockedAuthClient = jest.requireMock("@/auth/authClient").authClient as {
  signIn: jest.Mock;
  getSession: jest.Mock;
  signOut: jest.Mock;
  getToken: jest.Mock;
};

const mockedGetFavorites = apiGetFavorites as jest.MockedFunction<typeof apiGetFavorites>;
const mockedAddFavorite = apiAddFavorite as jest.MockedFunction<typeof apiAddFavorite>;
const mockedGetHistory = apiGetHistory as jest.MockedFunction<typeof apiGetHistory>;
const mockedAddHistory = apiAddHistory as jest.MockedFunction<typeof apiAddHistory>;

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
    jest.clearAllMocks();
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
      .mockResolvedValueOnce({ items: [serverFavorite] })
      .mockResolvedValueOnce({ items: [serverFavorite, localFavorite] });
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

    await waitFor(() => expect(mockedAddFavorite).toHaveBeenCalledWith(localFavorite.id));
    await waitFor(() =>
      expect(mockedAddHistory).toHaveBeenCalledWith({
        gymIds: [localHistoryA.id, localHistoryB.id],
      }),
    );

    await waitFor(() =>
      expect(favoritesStore.getState().favorites.map((favorite) => favorite.gym.id)).toEqual([
        serverFavorite.id,
        localFavorite.id,
      ]),
    );

    await waitFor(() =>
      expect(historyStore.getState().items.map((item) => item.id)).toEqual([
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
