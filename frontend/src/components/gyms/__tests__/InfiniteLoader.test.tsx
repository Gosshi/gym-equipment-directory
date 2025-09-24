import { render } from "@testing-library/react";
import { vi } from "vitest";

import { InfiniteLoader } from "@/components/gyms/InfiniteLoader";

describe("InfiniteLoader", () => {
  const observe = vi.fn();
  const disconnect = vi.fn();
  const observer = {
    observe: observe as unknown as (target: Element) => void,
    disconnect: disconnect as unknown as () => void,
  } as IntersectionObserver;
  const originalObserver = (global as { IntersectionObserver?: typeof IntersectionObserver })
    .IntersectionObserver;
  let trigger: ((entries: IntersectionObserverEntry[]) => void) | null = null;

  beforeAll(() => {
    (global as { IntersectionObserver?: typeof IntersectionObserver }).IntersectionObserver = vi.fn(
      (callback: IntersectionObserverCallback) => {
        trigger = (entries: IntersectionObserverEntry[]) => callback(entries, observer);
        return observer;
      },
    ) as unknown as typeof IntersectionObserver;
  });

  afterAll(() => {
    if (originalObserver) {
      (global as { IntersectionObserver?: typeof IntersectionObserver }).IntersectionObserver =
        originalObserver;
    } else {
      delete (global as { IntersectionObserver?: typeof IntersectionObserver })
        .IntersectionObserver;
    }
  });

  beforeEach(() => {
    observe.mockClear();
    disconnect.mockClear();
    trigger = null;
  });

  it("invokes onLoadMore when the sentinel intersects", () => {
    const onLoadMore = vi.fn();

    render(<InfiniteLoader enabled hasNextPage isLoading={false} onLoadMore={onLoadMore} />);

    expect(observe).toHaveBeenCalledTimes(1);
    expect(trigger).not.toBeNull();

    trigger?.([{ isIntersecting: true } as IntersectionObserverEntry]);

    expect(onLoadMore).toHaveBeenCalled();
  });

  it("does not trigger additional loads while already fetching", () => {
    const onLoadMore = vi.fn();

    render(<InfiniteLoader enabled hasNextPage isLoading onLoadMore={onLoadMore} />);

    trigger?.([{ isIntersecting: true } as IntersectionObserverEntry]);

    expect(onLoadMore).not.toHaveBeenCalled();
  });

  it("does not observe when infinite loading is disabled", () => {
    render(
      <InfiniteLoader
        enabled={false}
        hasNextPage={false}
        isLoading={false}
        onLoadMore={() => {}}
      />,
    );

    expect(observe).not.toHaveBeenCalled();
  });
});
