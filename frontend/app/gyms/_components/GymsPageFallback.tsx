export function GymsPageFallback() {
  return (
    <div className="flex min-h-screen flex-col gap-6 px-4 py-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <div className="space-y-3">
          <div className="h-4 w-28 animate-pulse rounded bg-muted" />
          <div className="h-8 w-44 animate-pulse rounded bg-muted" />
          <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
        </div>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-6">
            <div className="grid gap-4 rounded-lg border bg-card p-6 shadow-sm">
              <div className="h-10 w-full animate-pulse rounded bg-muted" />
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="h-10 w-full animate-pulse rounded bg-muted" />
                <div className="h-10 w-full animate-pulse rounded bg-muted" />
              </div>
            </div>
            <div className="grid gap-4 rounded-lg border bg-card p-6 shadow-sm">
              <div className="h-6 w-36 animate-pulse rounded bg-muted" />
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 6 }).map((_, index) => (
                  <div key={index} className="space-y-3 rounded-lg border p-4">
                    <div className="h-24 w-full animate-pulse rounded bg-muted" />
                    <div className="h-5 w-3/4 animate-pulse rounded bg-muted" />
                    <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="space-y-4">
            <div className="rounded-lg border bg-card p-6 shadow-sm">
              <div className="h-6 w-32 animate-pulse rounded bg-muted" />
              <div className="mt-4 h-10 w-full animate-pulse rounded bg-muted" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
