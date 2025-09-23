import { GymListSkeleton } from "@/components/gyms/GymListSkeleton";

export function GymsPageFallback() {
  return (
    <div className="flex min-h-screen flex-col gap-8 px-4 py-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
        <div className="space-y-3">
          <div className="h-4 w-28 animate-pulse rounded bg-muted" />
          <div className="h-8 w-44 animate-pulse rounded bg-muted" />
          <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
        </div>

        <div className="space-y-6">
          <div className="space-y-4 rounded-lg border bg-card p-6 shadow-sm">
            <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_200px_auto] md:items-end">
              <div className="space-y-2">
                <div className="h-4 w-20 animate-pulse rounded bg-muted" />
                <div className="h-10 w-full animate-pulse rounded bg-muted" />
              </div>
              <div className="space-y-2">
                <div className="h-4 w-24 animate-pulse rounded bg-muted" />
                <div className="h-10 w-full animate-pulse rounded bg-muted" />
              </div>
              <div className="flex justify-end">
                <div className="h-10 w-28 animate-pulse rounded bg-muted" />
              </div>
            </div>
            <div className="space-y-3">
              <div className="h-4 w-24 animate-pulse rounded bg-muted" />
              <div className="flex flex-wrap gap-2">
                {Array.from({ length: 5 }).map((_, index) => (
                  <div key={index} className="h-8 w-20 animate-pulse rounded-full bg-muted" />
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <div className="h-4 w-24 animate-pulse rounded bg-muted" />
              <div className="h-2 w-full animate-pulse rounded bg-muted" />
              <div className="h-3 w-40 animate-pulse rounded bg-muted" />
            </div>
          </div>

          <div className="space-y-4 rounded-lg border bg-card p-6 shadow-sm">
            <div className="h-6 w-36 animate-pulse rounded bg-muted" />
            <GymListSkeleton />
          </div>
        </div>
      </div>
    </div>
  );
}
