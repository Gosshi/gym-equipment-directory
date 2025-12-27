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
    // Hours and fees
    opening_hours: gym.openingHours,
    openingHours: gym.openingHours,
    fees: gym.fees,
    // Category-specific fields
    category: gym.category,
    pool_lanes: gym.poolLanes,
    pool_length_m: gym.poolLengthM,
    pool_heated: gym.poolHeated,
    court_type: gym.courtType,
    court_count: gym.courtCount,
    court_surface: gym.courtSurface,
    court_lighting: gym.courtLighting,
    hall_sports: gym.hallSports,
    hall_area_sqm: gym.hallAreaSqm,
    field_type: gym.fieldType,
    field_count: gym.fieldCount,
    field_lighting: gym.fieldLighting,
  } as any; // Casting to any to avoid strict type matching for now

  const normalized = normalizeGymDetail(apiResponse, gym.slug);

  // Structured data for Google rich snippets
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "SportsActivityLocation",
    name: gym.name,
    description: `${gym.prefecture ?? ""}${gym.city ?? ""}にある公営スポーツ施設`,
    address: {
      "@type": "PostalAddress",
      addressLocality: gym.city ?? undefined,
      addressRegion: gym.prefecture ?? undefined,
      addressCountry: "JP",
    },
    url: `${process.env.NEXT_PUBLIC_BASE_URL || "https://ironmap.app"}/gyms/${gym.slug}`,
    ...(gym.latitude && gym.longitude
      ? {
          geo: {
            "@type": "GeoCoordinates",
            latitude: gym.latitude,
            longitude: gym.longitude,
          },
        }
      : {}),
    ...(gym.website ? { sameAs: gym.website } : {}),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <GymDetailClient gym={normalized} />
    </>
  );
}
