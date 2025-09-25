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
    expect(state.lastInteraction).toBeNull();
    expect(state.lastSelectionSource).toBeNull();
    expect(state.lastSelectionAt).toBeNull();
  });

  it("updates selected and hovered ids", () => {
    const { setSelected, setHovered } = useMapSelectionStore.getState();

    setSelected(123, "map");
    setHovered(456, "map");

    const state = mapSelectionStore.getState();
    expect(state.selectedId).toBe(123);
    expect(state.hoveredId).toBe(456);
    expect(state.lastInteraction).toBe("map");
    expect(state.lastSelectionSource).toBe("map");
    expect(state.lastSelectionAt).toBeTypeOf("number");
  });

  it("keeps the selected id when the same value is set", () => {
    const { setSelected } = useMapSelectionStore.getState();

    setSelected(42, "list");
    expect(mapSelectionStore.getState().selectedId).toBe(42);

    const before = mapSelectionStore.getState().lastSelectionAt;
    setSelected(42, "map");
    expect(mapSelectionStore.getState().selectedId).toBe(42);
    expect(mapSelectionStore.getState().lastSelectionSource).toBe("map");
    expect(mapSelectionStore.getState().lastInteraction).toBe("map");
    expect(mapSelectionStore.getState().lastSelectionAt).toBeGreaterThanOrEqual(
      Number(before ?? 0),
    );
  });

  it("clears both ids", () => {
    useMapSelectionStore.setState({
      selectedId: 1,
      hoveredId: 2,
      lastInteraction: "map",
      lastSelectionSource: "map",
      lastSelectionAt: 123,
    });

    mapSelectionStore.getState().clear();

    const state = mapSelectionStore.getState();
    expect(state.selectedId).toBeNull();
    expect(state.hoveredId).toBeNull();
    expect(state.lastInteraction).toBeNull();
    expect(state.lastSelectionSource).toBeNull();
    expect(state.lastSelectionAt).toBeNull();
  });
});
