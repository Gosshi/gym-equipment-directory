import { useMemo } from "react";

import { Button } from "@/components/ui/button";

const ELLIPSIS = "ellipsis" as const;

type PaginationItem = number | typeof ELLIPSIS;

type PaginationProps = {
  currentPage: number;
  totalPages: number;
  hasNextPage: boolean;
  onChange: (page: number) => void;
  isLoading?: boolean;
  siblingCount?: number;
};

const range = (start: number, end: number): number[] =>
  Array.from({ length: end - start + 1 }, (_, index) => start + index);

export const buildPaginationRange = (
  currentPage: number,
  totalPages: number,
  siblingCount = 1,
): PaginationItem[] => {
  if (totalPages <= 0) {
    return [];
  }

  const totalPageNumbers = siblingCount * 2 + 5;

  if (totalPageNumbers >= totalPages) {
    return range(1, totalPages);
  }

  const clampedCurrent = Math.min(Math.max(currentPage, 1), totalPages);
  const leftSiblingIndex = Math.max(clampedCurrent - siblingCount, 1);
  const rightSiblingIndex = Math.min(clampedCurrent + siblingCount, totalPages);

  const showLeftEllipsis = leftSiblingIndex > 2;
  const showRightEllipsis = rightSiblingIndex < totalPages - 1;

  if (!showLeftEllipsis && showRightEllipsis) {
    const leftItemCount = 3 + 2 * siblingCount;
    const leftRange = range(1, leftItemCount);
    return [...leftRange, ELLIPSIS, totalPages];
  }

  if (showLeftEllipsis && !showRightEllipsis) {
    const rightItemCount = 3 + 2 * siblingCount;
    const rightRange = range(totalPages - rightItemCount + 1, totalPages);
    return [1, ELLIPSIS, ...rightRange];
  }

  const middleRange = range(leftSiblingIndex, rightSiblingIndex);
  return [1, ELLIPSIS, ...middleRange, ELLIPSIS, totalPages];
};

export function Pagination({
  currentPage,
  totalPages,
  hasNextPage,
  onChange,
  isLoading = false,
  siblingCount = 1,
}: PaginationProps) {
  const paginationRange = useMemo(
    () => buildPaginationRange(currentPage, totalPages, siblingCount),
    [currentPage, siblingCount, totalPages],
  );

  if (totalPages <= 1 && !hasNextPage) {
    return null;
  }

  const handleChange = (page: number) => {
    if (page < 1 || page === currentPage || (page > totalPages && !hasNextPage)) {
      return;
    }
    onChange(page);
  };

  const isPrevDisabled = isLoading || currentPage <= 1;
  const isNextDisabled = isLoading || (!hasNextPage && currentPage >= totalPages);

  return (
    <nav aria-label="ページネーション" className="flex justify-center">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          aria-label="前のページ"
          disabled={isPrevDisabled}
          onClick={() => handleChange(currentPage - 1)}
          type="button"
          variant="outline"
        >
          前へ
        </Button>
        <ul className="flex items-center gap-1">
          {paginationRange.map((item, index) => {
            if (item === ELLIPSIS) {
              return (
                <li key={`ellipsis-${index}`} className="px-2 text-sm text-muted-foreground" aria-hidden>
                  …
                </li>
              );
            }

            const pageNumber = item;
            const isActive = pageNumber === currentPage;
            return (
              <li key={pageNumber}>
                <Button
                  aria-current={isActive ? "page" : undefined}
                  aria-label={`ページ ${pageNumber}`}
                  onClick={() => handleChange(pageNumber)}
                  type="button"
                  variant={isActive ? "default" : "outline"}
                >
                  {pageNumber}
                </Button>
              </li>
            );
          })}
        </ul>
        <Button
          aria-label="次のページ"
          disabled={isNextDisabled}
          onClick={() => handleChange(currentPage + 1)}
          type="button"
        >
          次へ
        </Button>
      </div>
    </nav>
  );
}
