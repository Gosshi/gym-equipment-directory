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

const INITIAL_STATE: Omit<MapSelectionState, "setSelected" | "setHovered" | "clear"> = {
  selectedId: null,
  hoveredId: null,
  lastInteraction: null,
  lastSelectionSource: null,
  lastSelectionAt: null,
};

export const useMapSelectionStore = create<MapSelectionState>((set, get) => ({
  ...INITIAL_STATE,
  setSelected: (id, source) => {
    const state = get();
    const nextSelected = id ?? null;
    const update: Partial<MapSelectionState> = {};
    let shouldUpdate = false;

    if (state.selectedId !== nextSelected) {
      update.selectedId = nextSelected;
      shouldUpdate = true;
    }

    if (source) {
      if (state.lastInteraction !== source) {
        update.lastInteraction = source;
        shouldUpdate = true;
      }
      if (state.lastSelectionSource !== source) {
        update.lastSelectionSource = source;
        shouldUpdate = true;
      }

      const nextTimestamp = Date.now();
      if (!state.lastSelectionAt || state.lastSelectionAt !== nextTimestamp) {
        update.lastSelectionAt = nextTimestamp;
        shouldUpdate = true;
      }
    }

    if (!shouldUpdate) {
      return;
    }

    set(update);
  },
  setHovered: (id, source) => {
    const state = get();
    const nextHovered = id ?? null;
    const update: Partial<MapSelectionState> = {};
    let shouldUpdate = false;

    if (state.hoveredId !== nextHovered) {
      update.hoveredId = nextHovered;
      shouldUpdate = true;
    }

    if (source && state.lastInteraction !== source) {
      update.lastInteraction = source;
      shouldUpdate = true;
    }

    if (!shouldUpdate) {
      return;
    }

    set(update);
  },
  clear: () => {
    const state = get();
    if (
      state.selectedId === null &&
      state.hoveredId === null &&
      state.lastInteraction === null &&
      state.lastSelectionSource === null &&
      state.lastSelectionAt === null
    ) {
      return;
    }

    set({ ...INITIAL_STATE });
  },
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
