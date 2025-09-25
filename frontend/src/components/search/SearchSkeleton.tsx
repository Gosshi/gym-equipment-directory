import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type SearchSkeletonProps = {
  count?: number;
  className?: string;
  announce?: boolean;
};

const DEFAULT_SKELETON_COUNT = 6;

export function SearchSkeleton({
  count = DEFAULT_SKELETON_COUNT,
  className,
  announce = true,
}: SearchSkeletonProps) {
  const items = Array.from({ length: Math.max(count, DEFAULT_SKELETON_COUNT) });
  const rootProps = announce
    ? { "aria-live": "polite" as const }
    : { "aria-hidden": true as const };

  return (
    <div className="space-y-2" {...rootProps}>
      {announce ? (
        <span className="sr-only" role="status">
          検索結果を読み込み中です…
        </span>
      ) : null}
      <div
        aria-hidden="true"
        className={cn(
          "grid gap-4",
          "sm:grid-cols-2 sm:gap-6",
          "lg:grid-cols-2",
          "xl:grid-cols-3 xl:gap-7",
          "2xl:grid-cols-4",
          className,
        )}
      >
        {items.map((_, index) => (
          <Card data-testid="search-result-skeleton" key={index} className="overflow-hidden">
            <Skeleton className="h-40 w-full" />
            <CardContent className="space-y-3">
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <div className="flex gap-2">
                <Skeleton className="h-6 w-16 rounded-full" />
                <Skeleton className="h-6 w-16 rounded-full" />
                <Skeleton className="h-6 w-16 rounded-full" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
