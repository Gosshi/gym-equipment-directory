import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "トレーニングジム検索 | 公営ジム・フィットネス施設一覧",
  description:
    "全国の公営トレーニングジム・フィットネス施設を検索。マシンの種類や設備で絞り込み、最適なジムを見つけられます。料金や営業時間も確認できます。",
  keywords: [
    "公営ジム",
    "市営ジム",
    "トレーニングジム",
    "フィットネス",
    "筋トレ",
    "ウェイトトレーニング",
  ],
  openGraph: {
    title: "トレーニングジム検索 | 公営ジム・フィットネス施設一覧",
    description:
      "全国の公営トレーニングジム・フィットネス施設を検索。マシンの種類や設備で絞り込み、最適なジムを見つけられます。",
    type: "website",
  },
};

export default function GymPage() {
  redirect("/search?cats=gym");
}
