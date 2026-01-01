import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "テニスコート検索 | 公営テニスコート一覧",
  description:
    "全国の公営テニスコートを検索。クレーコート、オムニコート、ハードコートなど、条件に合ったテニスコートを見つけられます。ナイター照明の有無も確認できます。",
  keywords: [
    "公営テニスコート",
    "市営テニスコート",
    "テニス",
    "クレーコート",
    "オムニコート",
    "ナイター",
  ],
  openGraph: {
    title: "テニスコート検索 | 公営テニスコート一覧",
    description:
      "全国の公営テニスコートを検索。クレーコート、オムニコート、ハードコートなど、条件に合ったテニスコートを見つけられます。",
    type: "website",
  },
};

export default function TennisPage() {
  redirect("/search?cats=court");
}
