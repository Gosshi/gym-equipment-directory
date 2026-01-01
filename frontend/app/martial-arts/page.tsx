import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "武道場検索 | 公営武道場・道場一覧",
  description:
    "全国の公営武道場を検索。柔道場、剣道場、空手道場など、個人利用や団体利用できる武道施設を見つけられます。",
  keywords: ["公営武道場", "柔道場", "剣道場", "空手道場", "武道", "道場"],
  openGraph: {
    title: "武道場検索 | 公営武道場・道場一覧",
    description:
      "全国の公営武道場を検索。柔道場、剣道場、空手道場など、個人利用や団体利用できる武道施設を見つけられます。",
    type: "website",
  },
};

export default function MartialArtsPage() {
  redirect("/search?cats=martial_arts");
}
