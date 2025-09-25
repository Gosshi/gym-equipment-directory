"use client";

import { create } from "zustand";

import type { GymSummary } from "@/types/gym";

type GymId = GymSummary["id"];

export type MapInteractionSource = "map" | "list" | "url";

interface MapSelectionState {
  selectedId: GymId | null;
  hoveredId: GymId | null;
  lastInteraction: MapInteractionSource | null;
  lastSelectionSource: MapInteractionSource | null;
  lastSelectionAt: number | null;
  setSelected: (id: GymId | null, source?: MapInteractionSource) => void;
  setHovered: (id: GymId | null, source?: MapInteractionSource) => void;
  clear: () => void;
}

export const useMapSelectionStore = create<MapSelectionState>(set => ({
  selectedId: null,
  hoveredId: null,
  lastInteraction: null,
  lastSelectionSource: null,
  lastSelectionAt: null,
  setSelected: (id, source) =>
    set(state => {
      const nextSelected = id ?? null;
      const update: Partial<MapSelectionState> = {};

      if (state.selectedId !== nextSelected) {
        update.selectedId = nextSelected;
      }

      if (source) {
        update.lastInteraction = source;
        update.lastSelectionSource = source;
        update.lastSelectionAt = Date.now();
      }

      return Object.keys(update).length > 0 ? update : {};
    }),
  setHovered: (id, source) =>
    set(state => {
      const nextHovered = id ?? null;
      const update: Partial<MapSelectionState> = {};

      if (state.hoveredId !== nextHovered) {
        update.hoveredId = nextHovered;
      }

      if (source) {
        update.lastInteraction = source;
      }

      return Object.keys(update).length > 0 ? update : {};
    }),
  clear: () =>
    set({
      selectedId: null,
      hoveredId: null,
      lastInteraction: null,
      lastSelectionSource: null,
      lastSelectionAt: null,
    }),
}));

export const mapSelectionStore = useMapSelectionStore;

export const resetMapSelectionStoreForTests = () => {
  if (process.env.NODE_ENV === "production") {
    return;
  }

  useMapSelectionStore.setState({
    selectedId: null,
    hoveredId: null,
    lastInteraction: null,
    lastSelectionSource: null,
    lastSelectionAt: null,
  });
};
