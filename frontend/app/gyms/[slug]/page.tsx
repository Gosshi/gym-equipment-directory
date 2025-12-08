import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { getGymBySlug } from "@/services/gyms";
import { GymDetailClient } from "./GymDetailClient";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  try {
    const { slug } = await params;
    const gym = await getGymBySlug(slug);

    if (!gym) {
      return {
        title: "ジム詳細 | IRON MAP",
      };
    }

    const title = `${gym.name} | IRON MAP`;
    const description = `${gym.prefecture}${gym.city}にある「${gym.name}」の設備情報。${
      gym.equipments.length > 0 ? `主な設備: ${gym.equipments.slice(0, 5).join(", ")}など。` : ""
    }`;

    return {
      title,
      description,
      openGraph: {
        title,
        description,
        type: "website",
      },
    };
  } catch {
    return {
      title: "ジム詳細 | IRON MAP",
    };
  }
}

import { normalizeGymDetail } from "./normalization";

export default async function GymDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const gym = await getGymBySlug(slug);

  if (!gym) {
    notFound();
  }

  // Convert GymDetail to GymDetailApiResponse structure for normalization
  // This is a bit of a hack because getGymBySlug returns a domain model,
  // but normalizeGymDetail expects an API response.
  // Ideally, we should have a shared normalization for both.
  // For now, we construct a compatible object.
  const apiResponse = {
    gym: gym,
    slug: gym.slug,
    canonical_slug: gym.slug,
    requested_slug: slug,
    facilities: [], // Domain model uses equipments, not facilities structure like API
    facility_groups: [],
    equipment_details: [],
    equipments: gym.equipments,
    // Add other fields if necessary
  } as any; // Casting to any to avoid strict type matching for now

  const normalized = normalizeGymDetail(apiResponse, gym.slug);

  return <GymDetailClient gym={normalized} />;
}
