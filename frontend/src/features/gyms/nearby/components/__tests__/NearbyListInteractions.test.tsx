import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NearbyList } from "../NearbyList";
import type { NearbyListProps } from "../NearbyList";
import { resetMapSelectionStoreForTests, useMapSelectionStore } from "@/state/mapSelection";
import type { NearbyGym } from "@/types/gym";

const originalScrollIntoView = HTMLElement.prototype.scrollIntoView;

const gyms: NearbyGym[] = [
  {
    id: 1,
    slug: "gym-one",
    name: "ジムワン",
    prefecture: "東京都",
    city: "千代田区",
    latitude: 35.6895,
    longitude: 139.6917,
    distanceKm: 0.3,
  },
  {
    id: 2,
    slug: "gym-two",
    name: "ジムツー",
    prefecture: "東京都",
    city: "渋谷区",
    latitude: 35.6581,
    longitude: 139.7414,
    distanceKm: 1.2,
  },
];

const baseMeta = {
  total: gyms.length,
  page: 1,
  pageSize: 20,
  hasMore: false,
  hasPrev: false,
};

const noop = () => undefined;

const createRect = (top: number, bottom: number): DOMRect =>
  ({
    x: 0,
    y: top,
    top,
    bottom,
    left: 0,
    right: 0,
    height: bottom - top,
    width: 0,
    toJSON: () => ({}),
  }) as DOMRect;

const TestNearbyList = ({
  items = gyms,
  onOpenDetail = noop,
}: {
  items?: NearbyGym[];
  onOpenDetail?: NearbyListProps["onOpenDetail"];
}) => {
  const selectedId = useMapSelectionStore(state => state.selectedId);
  const setSelected = useMapSelectionStore(state => state.setSelected);

  return (
    <NearbyList
      error={null}
      isInitialLoading={false}
      isLoading={false}
      items={items}
      meta={{ ...baseMeta, total: items.length }}
      onOpenDetail={onOpenDetail}
      onPageChange={noop}
      onRetry={noop}
      onSelectGym={(id, source) => setSelected(id, source)}
      selectedGymId={selectedId}
    />
  );
};

const renderList = (items: NearbyGym[] = gyms, onOpenDetail = noop) =>
  render(<TestNearbyList items={items} onOpenDetail={onOpenDetail} />);

const getItemButton = async (gymId: number) => {
  const listItem = await screen.findByTestId(`gym-item-${gymId}`);
  const button = listItem.querySelector("button");
  if (!button) {
    throw new Error(`Button for gym ${gymId} was not found`);
  }
  return button;
};

beforeEach(() => {
  resetMapSelectionStoreForTests();
  vi.useRealTimers();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
    configurable: true,
    value: originalScrollIntoView,
  });
});

type TimeoutSpy = {
  mock: {
    calls: Array<[TimerHandler, ...unknown[]]>;
  };
};

const runLastTimeout = (spy: TimeoutSpy) => {
  const lastCall = spy.mock.calls.at(-1);
  if (!lastCall) {
    return;
  }

  const [handler] = lastCall;
  if (typeof handler === "function") {
    handler();
  }
};

describe("NearbyList map interactions", () => {
  it("applies selected styles and scrolls the item into view on selection", async () => {
    const scrollSpy = vi.fn();
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollSpy,
    });

    const timeoutSpy = vi.spyOn(window, "setTimeout");

    renderList();

    const list = screen.getByRole("listbox");
    Object.defineProperty(list, "scrollHeight", {
      configurable: true,
      get: () => 2000,
    });
    Object.defineProperty(list, "clientHeight", {
      configurable: true,
      get: () => 400,
    });
    list.getBoundingClientRect = () => createRect(0, 400);

    const item = screen.getByTestId("gym-item-2");
    item.getBoundingClientRect = () => createRect(900, 980);

    act(() => {
      useMapSelectionStore.getState().setSelected(2);
    });
    act(() => {
      runLastTimeout(timeoutSpy);
    });

    const target = await getItemButton(2);
    expect(target).toHaveClass("bg-primary/10");
    expect(target).toHaveClass("border-primary");
    expect(scrollSpy).toHaveBeenCalledTimes(1);
  });

  it("keeps the latest selection when markers are clicked consecutively", async () => {
    const scrollSpy = vi.fn();
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollSpy,
    });

    const timeoutSpy = vi.spyOn(window, "setTimeout");

    renderList();

    const list = screen.getByRole("listbox");
    Object.defineProperty(list, "scrollHeight", {
      configurable: true,
      get: () => 2000,
    });
    Object.defineProperty(list, "clientHeight", {
      configurable: true,
      get: () => 400,
    });
    list.getBoundingClientRect = () => createRect(0, 400);

    const firstItem = screen.getByTestId("gym-item-1");
    const secondItem = screen.getByTestId("gym-item-2");
    firstItem.getBoundingClientRect = () => createRect(450, 520);
    secondItem.getBoundingClientRect = () => createRect(900, 980);

    const firstButton = await getItemButton(1);
    const secondButton = await getItemButton(2);

    act(() => {
      fireEvent.click(firstButton);
    });
    act(() => {
      runLastTimeout(timeoutSpy);
    });

    expect(useMapSelectionStore.getState().selectedId).toBe(1);
    expect(scrollSpy).toHaveBeenCalledTimes(1);

    act(() => {
      fireEvent.click(secondButton);
    });
    act(() => {
      runLastTimeout(timeoutSpy);
    });

    expect(useMapSelectionStore.getState().selectedId).toBe(2);
    expect(scrollSpy).toHaveBeenCalledTimes(2);

    const target = await getItemButton(2);
    expect(target).toHaveClass("bg-primary/10");
  });

  it("shares the selection store across components", async () => {
    const timeoutSpy = vi.spyOn(window, "setTimeout");

    const SelectionObserver = () => {
      const selected = useMapSelectionStore(state => state.selectedId);
      return <div data-testid="selection-observer">{selected ?? "none"}</div>;
    };

    render(
      <>
        <SelectionObserver />
        <TestNearbyList items={gyms} />
      </>,
    );

    const button = await getItemButton(1);

    act(() => {
      fireEvent.click(button);
    });
    act(() => {
      runLastTimeout(timeoutSpy);
    });

    expect(screen.getByTestId("selection-observer")).toHaveTextContent("1");
  });
});
