import { Suspense } from "react";

import { NearbyGymsPage } from "@/features/gyms/nearby";

function NearbyPageFallback() {
  return (
    <div className="flex min-h-screen flex-col gap-6 px-4 py-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <div className="space-y-3">
          <div className="h-4 w-32 animate-pulse rounded bg-muted" />
          <div className="h-8 w-64 animate-pulse rounded bg-muted" />
          <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
        </div>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
          <div className="space-y-4">
            <div className="grid gap-4 rounded-lg border bg-card p-4 shadow-sm">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
                <div className="h-10 w-full animate-pulse rounded bg-muted" />
                <div className="h-10 w-full animate-pulse rounded bg-muted" />
              </div>
              <div className="h-10 w-full animate-pulse rounded bg-muted" />
              <div className="h-10 w-32 animate-pulse rounded bg-muted" />
            </div>
            <div className="h-[420px] w-full animate-pulse rounded-lg border bg-muted" />
          </div>
          <div className="space-y-3 rounded-lg border bg-card p-4 shadow-sm">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="space-y-2 rounded border p-4">
                <div className="h-5 w-2/3 animate-pulse rounded bg-muted" />
                <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
                <div className="h-4 w-1/3 animate-pulse rounded bg-muted" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function NearbyRoute() {
  return (
    <Suspense fallback={<NearbyPageFallback />}>
      <NearbyGymsPage />
    </Suspense>
  );
}
