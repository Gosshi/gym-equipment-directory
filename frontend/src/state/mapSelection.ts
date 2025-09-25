"use client";

import { create } from "zustand";

import type { GymSummary } from "@/types/gym";

type GymId = GymSummary["id"];

interface MapSelectionState {
  selectedId: GymId | null;
  hoveredId: GymId | null;
  setSelected: (id: GymId | null) => void;
  setHovered: (id: GymId | null) => void;
  clear: () => void;
}

export const useMapSelectionStore = create<MapSelectionState>(set => ({
  selectedId: null,
  hoveredId: null,
  setSelected: id =>
    set(() => ({
      selectedId: id ?? null,
    })),
  setHovered: id => set({ hoveredId: id }),
  clear: () => set({ selectedId: null, hoveredId: null }),
}));

export const mapSelectionStore = useMapSelectionStore;

export const resetMapSelectionStoreForTests = () => {
  if (process.env.NODE_ENV === "production") {
    return;
  }

  useMapSelectionStore.setState({ selectedId: null, hoveredId: null });
};
