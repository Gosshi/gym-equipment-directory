"use client";

import { useCallback, useState } from "react";
import Link from "next/link";

import { GymDetailPage } from "./GymDetailPage";
import { type NormalizedGymDetail } from "./normalization";

export function GymDetailClient({ gym }: { gym: NormalizedGymDetail }) {
  const [canonicalSlug, setCanonicalSlug] = useState(gym.slug);

  const handleCanonicalSlugChange = useCallback((next: string) => {
    setCanonicalSlug(prev => (prev === next ? prev : next));
  }, []);

  return (
    <>
      <GymDetailPage
        initialGym={gym}
        onCanonicalSlugChange={handleCanonicalSlugChange}
        slug={gym.slug}
      />
      <div className="px-4 pb-10">
        <div className="mx-auto w-full max-w-5xl">
          <Link
            aria-label="このジムの情報を報告する"
            className="mt-6 inline-flex text-sm font-medium text-muted-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            href={`/gyms/report/${canonicalSlug}`}
          >
            このジム情報に問題がありますか？報告する
          </Link>
        </div>
      </div>
    </>
  );
}
