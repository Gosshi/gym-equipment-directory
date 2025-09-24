import { useEffect, useRef } from "react";

type InfiniteLoaderProps = {
  enabled: boolean;
  hasNextPage: boolean;
  isLoading: boolean;
  onLoadMore: () => void;
  rootMargin?: string;
};

export function InfiniteLoader({
  enabled,
  hasNextPage,
  isLoading,
  onLoadMore,
  rootMargin = "400px",
}: InfiniteLoaderProps) {
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const loadMoreRef = useRef(onLoadMore);
  const pendingRef = useRef(false);

  useEffect(() => {
    loadMoreRef.current = onLoadMore;
  }, [onLoadMore]);

  useEffect(() => {
    if (!enabled || !hasNextPage) {
      pendingRef.current = false;
      return;
    }

    if (typeof IntersectionObserver === "undefined") {
      return;
    }

    const target = sentinelRef.current;
    if (!target) {
      return;
    }

    const observer = new IntersectionObserver(
      entries => {
        const entry = entries[0];
        if (!entry?.isIntersecting || isLoading || pendingRef.current) {
          return;
        }
        pendingRef.current = true;
        loadMoreRef.current();
      },
      { rootMargin },
    );

    observer.observe(target);

    return () => {
      observer.disconnect();
    };
  }, [enabled, hasNextPage, isLoading, rootMargin]);

  useEffect(() => {
    if (!isLoading) {
      pendingRef.current = false;
    }
  }, [isLoading]);

  return <div aria-hidden className="h-px w-full" ref={sentinelRef} />;
}
