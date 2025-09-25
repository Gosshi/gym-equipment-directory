import { useVirtualizer } from "@tanstack/react-virtual";
import type { JSX } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import type { GymSummary } from "@/types/gym";

const ROW_ESTIMATE = 340;
const COLUMN_BREAKPOINTS: Array<{ minWidth: number; columns: number }> = [
  { minWidth: 1536, columns: 4 },
  { minWidth: 1280, columns: 3 },
  { minWidth: 640, columns: 2 },
];

const ROW_PADDING_CLASSES = "pb-4 sm:pb-6 xl:pb-7";

const getColumnCount = (width: number) => {
  for (const breakpoint of COLUMN_BREAKPOINTS) {
    if (width >= breakpoint.minWidth) {
      return breakpoint.columns;
    }
  }
  if (width >= 768) {
    return 2;
  }
  return 1;
};

type VirtualizedGymGridProps = {
  gyms: GymSummary[];
  renderCard: (gym: GymSummary, index: number) => JSX.Element;
  className?: string;
  overscan?: number;
};

export function VirtualizedGymGrid({
  gyms,
  renderCard,
  className,
  overscan = 4,
}: VirtualizedGymGridProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [columns, setColumns] = useState(1);

  useEffect(() => {
    const element = scrollRef.current;
    if (!element || typeof ResizeObserver === "undefined") {
      return;
    }

    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        const width = entry.contentRect.width;
        const nextColumns = Math.max(1, getColumnCount(width));
        setColumns(previous => (previous === nextColumns ? previous : nextColumns));
      }
    });

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const rowCount = useMemo(() => {
    if (columns <= 0) {
      return 0;
    }
    return Math.ceil(gyms.length / columns);
  }, [columns, gyms.length]);

  const rowVirtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_ESTIMATE,
    overscan,
  });

  return (
    <div
      ref={scrollRef}
      className={cn(
        "relative max-h-[70vh] overflow-y-auto pr-1",
        "supports-[overflow:overlay]:pr-3",
        className,
      )}
    >
      <div
        aria-live="polite"
        className="relative"
        style={{ height: rowVirtualizer.getTotalSize() }}
      >
        {rowVirtualizer.getVirtualItems().map(virtualRow => {
          const startIndex = virtualRow.index * columns;
          const visibleGyms = gyms.slice(startIndex, startIndex + columns);

          return (
            <div
              key={virtualRow.key}
              ref={node => {
                if (node) {
                  rowVirtualizer.measureElement(node);
                }
              }}
              className={cn(ROW_PADDING_CLASSES)}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              <div
                className="grid gap-4 sm:gap-6 xl:gap-7"
                style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
              >
                {visibleGyms.map((gym, columnIndex) => {
                  const itemIndex = startIndex + columnIndex;
                  return (
                    <div className="h-full" key={`${gym.id ?? gym.slug ?? itemIndex}`}>
                      {renderCard(gym, itemIndex)}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
