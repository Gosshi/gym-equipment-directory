import { Suspense } from "react";

import { GymsPageFallback } from "@/app/gyms/_components/GymsPageFallback";
import { GymsPage } from "@/features/gyms/GymsPage";

export default function SearchRoute() {
  return (
    <Suspense fallback={<GymsPageFallback />}>
      <GymsPage />
    </Suspense>
  );
}
