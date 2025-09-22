import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { GymDetailPage } from "@/features/gyms/GymDetailPage";
import { addFavorite, removeFavorite } from "@/services/favorites";
import { getGymBySlug } from "@/services/gyms";
import { resetFavoriteStoreForTests } from "@/store/favorites";
import type { GymDetail } from "@/types/gym";

jest.mock("@/services/gyms", () => ({
  getGymBySlug: jest.fn(),
}));

jest.mock("@/services/favorites", () => ({
  addFavorite: jest.fn(),
  removeFavorite: jest.fn(),
}));

const mockedGetGymBySlug = getGymBySlug as jest.MockedFunction<typeof getGymBySlug>;
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

describe("GymDetailPage favorite toggle", () => {
  beforeEach(() => {
    resetFavoriteStoreForTests();
    window.localStorage.clear();
    jest.clearAllMocks();

    mockedGetGymBySlug.mockResolvedValue(mockGymDetail);
    mockedAddFavorite.mockResolvedValue(undefined);
    mockedRemoveFavorite.mockResolvedValue(undefined);
  });

  it("adds a gym to favorites and persists to localStorage", async () => {
    const user = userEvent.setup();

    render(<GymDetailPage slug="sample-gym" />);

    await screen.findByRole("heading", { name: mockGymDetail.name });

    const button = await screen.findByRole("button", { name: /お気に入り/ });

    await user.click(button);

    expect(mockedAddFavorite).toHaveBeenCalledWith(mockGymDetail.id);

    await waitFor(() => expect(button).toHaveTextContent("お気に入り済み"));
    await waitFor(() => {
      expect(window.localStorage.getItem("favoriteGymIds")).toBe(
        JSON.stringify([mockGymDetail.id]),
      );
    });
  });

  it("removes a gym from favorites and updates localStorage", async () => {
    window.localStorage.setItem("favoriteGymIds", JSON.stringify([mockGymDetail.id]));
    const user = userEvent.setup();

    render(<GymDetailPage slug="sample-gym" />);

    await screen.findByRole("heading", { name: mockGymDetail.name });

    // Wait for the button to reflect the initial favorite state.
    const button = await screen.findByRole("button", { name: /お気に入り済み/ });

    await user.click(button);

    expect(mockedRemoveFavorite).toHaveBeenCalledWith(mockGymDetail.id);

    await waitFor(() => expect(button).toHaveTextContent("☆ お気に入り"));
    await waitFor(() => {
      expect(window.localStorage.getItem("favoriteGymIds")).toBe(JSON.stringify([]));
    });
  });
});
