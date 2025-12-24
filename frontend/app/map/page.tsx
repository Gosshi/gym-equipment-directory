import { Suspense } from "react";
import { MapSearchPage } from "@/features/map/MapSearchPage";
import { Metadata } from "next";
import { Loader2 } from "lucide-react";

export const metadata: Metadata = {
  title: "地図からジムを探す | ジム設備ディレクトリ",
  description: "地図上で位置を指定して、近くのジムや設備を検索できます。",
};

export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="h-[calc(100vh-64px)] w-full flex items-center justify-center bg-gray-100">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      }
    >
      <MapSearchPage />
    </Suspense>
  );
}
