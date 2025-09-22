import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { GymEquipmentTabs } from "@/components/gyms/GymEquipmentTabs";
import type { GymEquipmentDetail } from "@/types/gym";

describe("GymEquipmentTabs", () => {
  const sampleEquipments: GymEquipmentDetail[] = [
    { id: 1, name: "スミスマシン", category: "マシン", description: "スミスマシンは安全にスクワットが行えます。" },
    { id: 2, name: "パワーラック", category: "フリーウェイト" },
    { id: 3, name: "トレッドミル", category: "有酸素", description: "ランニングマシン" },
    { id: 4, name: "ストレッチマット" },
  ];

  it("shows all equipments by default and filters by category", async () => {
    const user = userEvent.setup();

    render(<GymEquipmentTabs equipments={sampleEquipments} />);

    expect(screen.getByRole("tab", { name: "全て (4)" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "マシン (1)" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("tab", { name: "フリーウェイト (1)" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "有酸素 (1)" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "その他 (1)" })).toBeInTheDocument();

    // all equipments should be visible initially
    expect(screen.getByText("スミスマシン")).toBeInTheDocument();
    expect(screen.getByText("パワーラック")).toBeInTheDocument();
    expect(screen.getByText("トレッドミル")).toBeInTheDocument();
    expect(screen.getByText("ストレッチマット")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "有酸素 (1)" }));

    expect(screen.getByRole("tab", { name: "有酸素 (1)" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("トレッドミル")).toBeInTheDocument();
    expect(screen.queryByText("スミスマシン")).not.toBeInTheDocument();
    expect(screen.queryByText("パワーラック")).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "その他 (1)" }));

    expect(screen.getByText("ストレッチマット")).toBeInTheDocument();
    expect(screen.queryByText("トレッドミル")).not.toBeInTheDocument();
  });
});
