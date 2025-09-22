import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AuthProvider } from "@/auth/AuthProvider";
import { GymDetailPage } from "@/features/gyms/GymDetailPage";
import { getFavorites, addFavorite, removeFavorite, getHistory, addHistory } from "@/lib/apiClient";
import { getGymBySlug } from "@/services/gyms";
import { resetFavoritesStoreForTests } from "@/store/favoritesStore";
import { resetHistoryStoreForTests } from "@/store/historyStore";
import type { GymDetail, GymSummary } from "@/types/gym";

jest.mock("@/services/gyms", () => ({
  getGymBySlug: jest.fn(),
}));

jest.mock("@/lib/apiClient", () => ({
  getFavorites: jest.fn(),
  addFavorite: jest.fn(),
  removeFavorite: jest.fn(),
  getHistory: jest.fn(),
  addHistory: jest.fn(),
}));

const mockedGetGymBySlug = getGymBySlug as jest.MockedFunction<typeof getGymBySlug>;
const mockedGetFavorites = getFavorites as jest.MockedFunction<typeof getFavorites>;
const mockedAddFavorite = addFavorite as jest.MockedFunction<typeof addFavorite>;
const mockedRemoveFavorite = removeFavorite as jest.MockedFunction<typeof removeFavorite>;
const mockedGetHistory = getHistory as jest.MockedFunction<typeof getHistory>;
const mockedAddHistory = addHistory as jest.MockedFunction<typeof addHistory>;

const mockGymDetail: GymDetail = {
  id: 101,
  slug: "sample-gym",
  name: "Sample Gym",
  prefecture: "tokyo",
  city: "chiyoda",
  address: "東京都千代田区1-1",
  equipments: ["Bench Press", "Squat Rack"],
  thumbnailUrl: "https://example.com/image.jpg",
  images: ["https://example.com/image.jpg"],
  openingHours: "09:00-21:00",
  phone: "03-0000-0000",
  website: "https://sample.example.com",
  description: "テスト用のジム詳細です。",
};

const toSummary = (detail: GymDetail): GymSummary => ({
  id: detail.id,
  slug: detail.slug,
  name: detail.name,
  prefecture: detail.prefecture,
  city: detail.city,
  address: detail.address,
  thumbnailUrl: detail.thumbnailUrl ?? null,
  lastVerifiedAt: null,
});

const mockSummary = toSummary(mockGymDetail);

describe("GymDetailPage favorite toggle", () => {
  beforeEach(() => {
    resetFavoritesStoreForTests();
    resetHistoryStoreForTests();
    window.localStorage.clear();
    window.localStorage.setItem(
      "ged.auth.session",
      JSON.stringify({
        token: "stub.test-token",
        user: {
          id: "test-user",
          name: "Test User",
        },
      }),
    );

    jest.clearAllMocks();

    mockedGetGymBySlug.mockResolvedValue(mockGymDetail);
    mockedGetHistory.mockResolvedValue({ items: [] });
    mockedAddHistory.mockResolvedValue(undefined);
  });

  it("adds a gym to favorites and updates the toggle label", async () => {
    mockedGetFavorites
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          gym_id: mockSummary.id,
          slug: mockSummary.slug,
          name: mockSummary.name,
          pref: mockSummary.prefecture,
          city: mockSummary.city,
          last_verified_at: mockSummary.lastVerifiedAt,
        },
      ]);
    mockedAddFavorite.mockResolvedValue(undefined);

    const user = userEvent.setup();

    render(
      <AuthProvider>
        <GymDetailPage slug="sample-gym" />
      </AuthProvider>,
    );

    await screen.findByRole("heading", { name: mockGymDetail.name });

    const button = await screen.findByRole("button", { name: /お気に入りに追加/ });
    await waitFor(() => expect(button).toBeEnabled());
    expect(button).toHaveTextContent("お気に入りに追加");

    await user.click(button);

    await waitFor(() =>
      expect(mockedAddFavorite).toHaveBeenCalledWith(expect.any(String), mockGymDetail.id),
    );

    await waitFor(() => expect(button).toHaveTextContent("お気に入り済み"));
  });

  it("removes a gym from favorites and updates the toggle label", async () => {
    mockedGetFavorites
      .mockResolvedValueOnce([
        {
          gym_id: mockSummary.id,
          slug: mockSummary.slug,
          name: mockSummary.name,
          pref: mockSummary.prefecture,
          city: mockSummary.city,
          last_verified_at: mockSummary.lastVerifiedAt,
        },
      ])
      .mockResolvedValueOnce([
        {
          gym_id: mockSummary.id,
          slug: mockSummary.slug,
          name: mockSummary.name,
          pref: mockSummary.prefecture,
          city: mockSummary.city,
          last_verified_at: mockSummary.lastVerifiedAt,
        },
      ])
      .mockResolvedValueOnce([]);
    mockedRemoveFavorite.mockResolvedValue(undefined);

    const user = userEvent.setup();

    render(
      <AuthProvider>
        <GymDetailPage slug="sample-gym" />
      </AuthProvider>,
    );

    await screen.findByRole("heading", { name: mockGymDetail.name });

    const button = await screen.findByRole("button", { name: /お気に入り済み/ });
    await waitFor(() => expect(button).toBeEnabled());

    await user.click(button);

    await waitFor(() =>
      expect(mockedRemoveFavorite).toHaveBeenCalledWith(expect.any(String), mockGymDetail.id),
    );

    await waitFor(() => expect(button).toHaveTextContent("お気に入りに追加"));
  });
});
