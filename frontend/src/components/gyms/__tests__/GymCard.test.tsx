import { render, screen } from "@testing-library/react";

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
  it("renders key gym information and navigation link", () => {
    const gym = buildGym();

    render(<GymCard gym={gym} />);

    const link = screen.getByRole("link", { name: /新宿ストレングスジム/ });
    expect(link).toHaveAttribute("href", "/gyms/shinjuku-strength");
    expect(screen.getByRole("img", { name: gym.name })).toHaveAttribute(
      "src",
      "https://example.com/thumb.jpg",
    );
    expect(screen.getByText("東京都 / 新宿区")).toBeInTheDocument();
    expect(screen.getByText("パワーラック")).toBeInTheDocument();
    expect(screen.getByText("ダンベル")).toBeInTheDocument();
  });

  it("shows placeholders when thumbnail and equipments are missing", () => {
    const gym = buildGym({ equipments: [], thumbnailUrl: null });

    render(<GymCard gym={gym} />);

    expect(screen.getByText("画像なし")).toBeInTheDocument();
    expect(screen.getByText("設備情報はまだ登録されていません。")).toBeInTheDocument();
  });
});
