import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "グラウンド・野球場検索 | 公営グラウンド一覧",
  description:
    "全国の公営グラウンド・野球場・サッカー場を検索。ナイター設備や人工芝など、条件に合った施設を見つけられます。予約情報も確認できます。",
  keywords: ["公営グラウンド", "野球場", "サッカー場", "運動場", "ナイター", "人工芝"],
  openGraph: {
    title: "グラウンド・野球場検索 | 公営グラウンド一覧",
    description:
      "全国の公営グラウンド・野球場・サッカー場を検索。ナイター設備や人工芝など、条件に合った施設を見つけられます。",
    type: "website",
  },
};

export default function FieldPage() {
  redirect("/search?cats=field");
}
