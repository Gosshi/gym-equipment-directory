import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "体育館検索 | 公営体育館・スポーツホール一覧",
  description:
    "全国の公営体育館・スポーツホールを検索。バスケットボール、バレーボール、バドミントンなど、個人利用できる体育館を見つけられます。",
  keywords: [
    "公営体育館",
    "市民体育館",
    "スポーツホール",
    "バスケットボール",
    "バレーボール",
    "バドミントン",
    "個人利用",
  ],
  openGraph: {
    title: "体育館検索 | 公営体育館・スポーツホール一覧",
    description:
      "全国の公営体育館・スポーツホールを検索。バスケ、バレー、バドミントンなど、個人利用できる体育館を見つけられます。",
    type: "website",
  },
};

export default function HallPage() {
  redirect("/search?cats=hall");
}
