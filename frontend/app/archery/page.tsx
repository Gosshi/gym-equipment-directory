import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "弓道場検索 | 公営弓道場一覧",
  description:
    "全国の公営弓道場を検索。初心者から経験者まで利用できる弓道施設を見つけられます。個人利用・団体利用の情報も確認できます。",
  keywords: ["公営弓道場", "弓道", "弓道場", "アーチェリー"],
  openGraph: {
    title: "弓道場検索 | 公営弓道場一覧",
    description: "全国の公営弓道場を検索。初心者から経験者まで利用できる弓道施設を見つけられます。",
    type: "website",
  },
};

export default function ArcheryPage() {
  redirect("/search?cats=archery");
}
