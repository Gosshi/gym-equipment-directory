import userEvent from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { GymCard } from "@/components/gyms/GymCard";
import type { GymSummary } from "@/types/gym";

const buildGym = (overrides: Partial<GymSummary> = {}): GymSummary => ({
  id: 1,
  slug: "shinjuku-strength",
  name: "新宿ストレングスジム",
  prefecture: "東京都",
  city: "新宿区",
  address: "東京都新宿区1-1-1",
  equipments: ["パワーラック", "ダンベル"],
  thumbnailUrl: "https://example.com/thumb.jpg",
  lastVerifiedAt: "2024-09-01T12:00:00Z",
  ...overrides,
});

describe("GymCard", () => {
  it("renders gym information, trims equipments, and exposes navigation link", () => {
    const gym = buildGym({
      equipments: [
        "パワーラック",
        "ダンベル",
        "バーベル",
        "ケーブルマシン",
        "トレッドミル",
        "エアロバイク",
      ],
    });

    render(<GymCard gym={gym} />);

    const link = screen.getByRole("link", { name: "新宿ストレングスジムの詳細を見る" });
    expect(link).toHaveAttribute("href", "/gyms/shinjuku-strength");
    expect(screen.getByRole("img", { name: gym.name })).toHaveAttribute(
      "src",
      "https://example.com/thumb.jpg",
    );
    expect(screen.getByTestId("gym-address")).toHaveTextContent("東京都新宿区1-1-1");

    const equipments = screen.getByTestId("gym-equipments");
    expect(equipments).toHaveTextContent("パワーラック");
    expect(equipments).toHaveTextContent("ダンベル");
    expect(equipments).toHaveTextContent("バーベル");
    expect(equipments).toHaveTextContent("ケーブルマシン");
    expect(equipments).toHaveTextContent("トレッドミル");
    expect(equipments).toHaveTextContent("+1");
  });

  it("shows placeholders when thumbnail and equipments are missing", () => {
    const gym = buildGym({ equipments: [], thumbnailUrl: null });

    render(<GymCard gym={gym} />);

    expect(screen.getByText("画像なし")).toBeInTheDocument();
    expect(screen.getByText("設備情報はまだ登録されていません。")).toBeInTheDocument();
  });

  it("falls back to prefecture and city when address is unavailable", () => {
    const gym = buildGym({ address: undefined });

    render(<GymCard gym={gym} />);

    expect(screen.getByTestId("gym-address")).toHaveTextContent("東京都 新宿区");
  });

  it("supports keyboard navigation by triggering click on space key", async () => {
    const gym = buildGym();
    const user = userEvent.setup();

    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);

    render(<GymCard gym={gym} />);

    const link = screen.getByRole("link", { name: "新宿ストレングスジムの詳細を見る" });
    link.focus();

    await user.keyboard(" ");

    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();
  });
});
