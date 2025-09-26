"use client";

import { create } from "zustand";

import type { GymSummary } from "@/types/gym";

type GymId = GymSummary["id"];

export type MapInteractionSource = "map" | "list" | "url";

interface MapSelectionState {
  selectedId: GymId | null;
  lastInteraction: MapInteractionSource | null;
  lastSelectionSource: MapInteractionSource | null;
  lastSelectionAt: number | null;
  setSelected: (id: GymId | null, source?: MapInteractionSource) => void;
  clear: () => void;
}

const INITIAL_STATE: Omit<MapSelectionState, "setSelected" | "clear"> = {
  selectedId: null,
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

    const selectionChanged = state.selectedId !== nextSelected;
    const sourceChanged = source ? state.lastSelectionSource !== source : false;
    const interactionChanged = source ? state.lastInteraction !== source : false;

    if (selectionChanged) {
      update.selectedId = nextSelected;
      shouldUpdate = true;
    }

    if (interactionChanged) {
      update.lastInteraction = source!;
      shouldUpdate = true;
    }

    if (sourceChanged) {
      update.lastSelectionSource = source!;
      shouldUpdate = true;
    }

    const shouldRefreshTimestamp =
      source != null && (selectionChanged || sourceChanged || source !== "url");

    if (shouldRefreshTimestamp) {
      const now = Date.now();
      const previous = state.lastSelectionAt ?? 0;
      update.lastSelectionAt = now <= previous ? previous + 1 : now;
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
    lastInteraction: null,
    lastSelectionSource: null,
    lastSelectionAt: null,
  });
};
