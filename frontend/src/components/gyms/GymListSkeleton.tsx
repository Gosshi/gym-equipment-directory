import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type GymListSkeletonProps = {
  /**
   * Number of placeholder cards to render.
   * Defaults to 6 to fill a 3-column grid.
   */
  count?: number;
};

export function GymListSkeleton({ count = 6 }: GymListSkeletonProps) {
  return (
    <div
      aria-hidden
      className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
      role="presentation"
    >
      {Array.from({ length: count }).map((_, index) => (
        <Card key={index} className="overflow-hidden">
          <Skeleton className="h-40 w-full" />
          <CardHeader className="space-y-3">
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex gap-2">
              <Skeleton className="h-6 w-16 rounded-full" />
              <Skeleton className="h-6 w-16 rounded-full" />
              <Skeleton className="h-6 w-16 rounded-full" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
