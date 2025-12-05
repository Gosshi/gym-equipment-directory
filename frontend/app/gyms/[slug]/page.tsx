import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { getGymBySlug } from "@/services/gyms";
import { GymDetailClient } from "./GymDetailClient";

interface Props {
  params: { slug: string };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  try {
    const gym = await getGymBySlug(params.slug);

    const title = `${gym.name} | IRON MAP`;
    const description = `${gym.prefecture}${gym.city}にある「${gym.name}」の設備情報。${
      gym.equipments.length > 0 ? `主な設備: ${gym.equipments.slice(0, 5).join(", ")}など。` : ""
    }パワーラック、ダンベル、マシンの有無をチェックして、最高のトレーニング環境を見つけよう。`;

    return {
      title,
      description,
      openGraph: {
        title,
        description,
        type: "website",
        locale: "ja_JP",
        siteName: "IRON MAP",
      },
      twitter: {
        card: "summary_large_image",
        title,
        description,
      },
    };
  } catch (error) {
    return {
      title: "ジム詳細 | IRON MAP",
      description: "ジムの設備情報をチェックして、最高のトレーニング環境を見つけよう。",
    };
  }
}

export default function GymDetailRoute({ params }: Props) {
  return <GymDetailClient slug={params.slug} />;
}
