import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GymsPage } from "@/features/gyms/GymsPage";
import { searchGyms } from "@/services/gyms";
import type { GymSummary } from "@/types/gym";

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(),
  usePathname: jest.fn(),
}));

jest.mock("@/services/gyms", () => ({
  searchGyms: jest.fn(),
}));

const { useRouter, useSearchParams, usePathname } = jest.requireMock("next/navigation") as {
  useRouter: jest.Mock;
  useSearchParams: jest.Mock;
  usePathname: jest.Mock;
};

const mockRouter = { push: jest.fn() };

const buildGym = (overrides: Partial<GymSummary> = {}): GymSummary => ({
  id: 1,
  slug: "test-gym",
  name: "テストジム",
  prefecture: "tokyo",
  city: "shinjuku",
  equipments: ["Squat Rack"],
  thumbnailUrl: null,
  score: 1.2,
  lastVerifiedAt: "2024-09-01T12:00:00Z",
  ...overrides,
});

describe("GymsPage", () => {
  beforeEach(() => {
    useRouter.mockReturnValue(mockRouter);
    useSearchParams.mockReturnValue(new URLSearchParams());
    usePathname.mockReturnValue("/gyms");
    (searchGyms as jest.Mock).mockResolvedValue({
      items: [buildGym()],
      meta: { total: 1, hasNext: false, pageToken: null },
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the search form and fetched gyms", async () => {
    render(<GymsPage />);

    expect(screen.getByLabelText("キーワード")).toBeInTheDocument();
    expect(screen.getByLabelText("都道府県スラッグ")).toBeInTheDocument();
    expect(screen.getByLabelText("市区町村スラッグ")).toBeInTheDocument();

    await waitFor(() => expect(searchGyms).toHaveBeenCalled());
    expect(await screen.findByText("テストジム")).toBeInTheDocument();
    expect(screen.getByText("1 件のジムが見つかりました。")).toBeInTheDocument();
  });

  it("pushes query params when submitting the form", async () => {
    const user = userEvent.setup();
    render(<GymsPage />);

    await waitFor(() => expect(searchGyms).toHaveBeenCalled());

    const keywordInput = screen.getByLabelText("キーワード");
    await user.clear(keywordInput);
    await user.type(keywordInput, "bench");
    await user.click(screen.getByRole("button", { name: "検索" }));

    expect(mockRouter.push).toHaveBeenCalledWith("/gyms?q=bench", { scroll: false });
  });
});
