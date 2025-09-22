import { Suspense } from "react";

import { GymsPageFallback } from "./_components/GymsPageFallback";
import { GymsPage } from "@/features/gyms/GymsPage";

export default function GymsRoute() {
  return (
    <Suspense fallback={<GymsPageFallback />}>
      <GymsPage />
    </Suspense>
  );
}
