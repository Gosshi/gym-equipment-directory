import { describe, expect, beforeEach, it } from "vitest";

import {
  mapSelectionStore,
  resetMapSelectionStoreForTests,
  useMapSelectionStore,
} from "@/state/mapSelection";

describe("mapSelectionStore", () => {
  beforeEach(() => {
    resetMapSelectionStoreForTests();
  });

  it("provides null defaults", () => {
    const state = mapSelectionStore.getState();
    expect(state.selectedId).toBeNull();
    expect(state.hoveredId).toBeNull();
  });

  it("updates selected and hovered ids", () => {
    const { setSelected, setHovered } = useMapSelectionStore.getState();

    setSelected(123);
    setHovered(456);

    const state = mapSelectionStore.getState();
    expect(state.selectedId).toBe(123);
    expect(state.hoveredId).toBe(456);
  });

  it("clears both ids", () => {
    useMapSelectionStore.setState({ selectedId: 1, hoveredId: 2 });

    mapSelectionStore.getState().clear();

    const state = mapSelectionStore.getState();
    expect(state.selectedId).toBeNull();
    expect(state.hoveredId).toBeNull();
  });
});
