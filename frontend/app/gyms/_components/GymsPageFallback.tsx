export function GymsPageFallback() {
  return (
    <div className="flex min-h-screen w-full flex-col bg-muted/10">
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-4 pb-16 pt-8 sm:gap-10 sm:pt-12 lg:px-6 xl:px-0">
        <div className="space-y-3 sm:space-y-4">
          <div className="h-3.5 w-24 animate-pulse rounded-full bg-muted" />
          <div className="h-8 w-48 animate-pulse rounded-full bg-muted" />
          <div className="h-4 w-3/4 animate-pulse rounded-full bg-muted" />
        </div>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)] lg:items-start xl:grid-cols-[minmax(0,380px)_minmax(0,1fr)] xl:gap-8">
          <div className="space-y-4">
            <div className="flex flex-col gap-4 rounded-2xl border border-border/80 bg-card/95 p-6 shadow-sm sm:p-7">
              <div className="h-10 w-full animate-pulse rounded-md bg-muted" />
              <div className="h-10 w-full animate-pulse rounded-md bg-muted" />
              <div className="h-20 w-full animate-pulse rounded-xl bg-muted/70" />
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="h-10 w-full animate-pulse rounded-md bg-muted" />
                <div className="h-10 w-full animate-pulse rounded-md bg-muted" />
              </div>
              <div className="h-32 w-full animate-pulse rounded-xl border border-dashed border-muted-foreground/30 bg-muted/40" />
            </div>
            <div className="rounded-2xl border border-border/80 bg-card/95 p-6 shadow-sm sm:p-7">
              <div className="h-6 w-32 animate-pulse rounded bg-muted" />
              <div className="mt-4 h-10 w-full animate-pulse rounded bg-muted" />
            </div>
          </div>
          <div className="space-y-6">
            <div className="rounded-2xl border border-border/80 bg-card/95 p-6 shadow-sm sm:p-8">
              <div className="h-6 w-28 animate-pulse rounded bg-muted" />
              <div className="mt-6 grid gap-4 sm:grid-cols-2 sm:gap-6 xl:grid-cols-3 xl:gap-7">
                {Array.from({ length: 6 }).map((_, index) => (
                  <div
                    key={index}
                    className="space-y-3 rounded-xl border border-border/70 bg-background/80 p-4"
                  >
                    <div className="h-28 w-full animate-pulse rounded-lg bg-muted" />
                    <div className="h-5 w-3/4 animate-pulse rounded bg-muted" />
                    <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-border/80 bg-card/95 p-6 shadow-sm sm:p-8">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="h-4 w-32 animate-pulse rounded bg-muted" />
                <div className="h-9 w-36 animate-pulse rounded bg-muted" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
