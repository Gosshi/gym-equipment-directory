import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AuthProvider } from "@/auth/AuthProvider";
import { GymDetailPage } from "@/features/gyms/GymDetailPage";
import { addFavorite, listFavorites, removeFavorite } from "@/services/favorites";
import { getGymBySlug } from "@/services/gyms";
import { resetFavoriteStoreForTests } from "@/store/favorites";
import type { Favorite } from "@/types/favorite";
import type { GymDetail } from "@/types/gym";

jest.mock("@/services/gyms", () => ({
  getGymBySlug: jest.fn(),
}));

jest.mock("@/services/favorites", () => ({
  listFavorites: jest.fn(),
  addFavorite: jest.fn(),
  removeFavorite: jest.fn(),
}));

const mockedGetGymBySlug = getGymBySlug as jest.MockedFunction<typeof getGymBySlug>;
const mockedListFavorites = listFavorites as jest.MockedFunction<typeof listFavorites>;
const mockedAddFavorite = addFavorite as jest.MockedFunction<typeof addFavorite>;
const mockedRemoveFavorite = removeFavorite as jest.MockedFunction<typeof removeFavorite>;

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

const mockFavorite: Favorite = {
  createdAt: "2024-09-10T10:00:00Z",
  gym: {
    id: mockGymDetail.id,
    slug: mockGymDetail.slug,
    name: mockGymDetail.name,
    prefecture: mockGymDetail.prefecture,
    city: mockGymDetail.city,
    address: mockGymDetail.address,
    thumbnailUrl: mockGymDetail.thumbnailUrl,
    lastVerifiedAt: null,
  },
};

describe("GymDetailPage favorite toggle", () => {
  beforeEach(() => {
    resetFavoriteStoreForTests();
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
    mockedAddFavorite.mockResolvedValue(undefined);
    mockedRemoveFavorite.mockResolvedValue(undefined);
  });

  it("adds a gym to favorites and updates the toggle label", async () => {
    mockedListFavorites
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([mockFavorite]);

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
      expect(mockedAddFavorite).toHaveBeenCalledWith(
        mockGymDetail.id,
        expect.stringMatching(/^[A-Za-z0-9_-]{8,128}$/),
      ),
    );

    await waitFor(() => expect(button).toHaveTextContent("お気に入り済み"));
  });

  it("removes a gym from favorites and updates the toggle label", async () => {
    mockedListFavorites
      .mockResolvedValueOnce([mockFavorite])
      .mockResolvedValueOnce([]);

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
      expect(mockedRemoveFavorite).toHaveBeenCalledWith(
        mockGymDetail.id,
        expect.stringMatching(/^[A-Za-z0-9_-]{8,128}$/),
      ),
    );

    await waitFor(() => expect(button).toHaveTextContent("お気に入りに追加"));
  });
});
