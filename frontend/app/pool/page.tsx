import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "プール・水泳施設検索 | 公営プール一覧",
  description:
    "全国の公営プール・市民プールを検索。温水プール、50mプール、屋内プールなど、条件に合った水泳施設を見つけられます。レーン数や営業時間も確認できます。",
  keywords: ["公営プール", "市民プール", "温水プール", "50mプール", "水泳", "スイミング"],
  openGraph: {
    title: "プール・水泳施設検索 | 公営プール一覧",
    description:
      "全国の公営プール・市民プールを検索。温水プール、50mプール、屋内プールなど、条件に合った水泳施設を見つけられます。",
    type: "website",
  },
};

export default function PoolPage() {
  redirect("/search?cats=pool");
}
