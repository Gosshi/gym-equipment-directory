import { MapSearchPage } from "@/features/map/MapSearchPage";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "地図からジムを探す | ジム設備ディレクトリ",
  description: "地図上で位置を指定して、近くのジムや設備を検索できます。",
};

export default function Page() {
  return <MapSearchPage />;
}
