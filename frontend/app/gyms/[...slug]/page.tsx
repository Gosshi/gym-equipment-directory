import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { getGymBySlug } from "@/services/gyms";
import { GymDetailClient } from "./GymDetailClient";
import { generateSeoTitle, generateSeoDescription } from "./seo";

interface PageProps {
  params: Promise<{ slug: string[] }>;
}

/**
 * Join slug segments into a single path string.
 * Supports hierarchical URLs like /tokyo/suginami/tac-kamiigusa
 */
function joinSlug(slugParts: string[]): string {
  return slugParts.join("/");
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || "https://spomap.jp";

  try {
    const { slug: slugParts } = await params;
    const slug = joinSlug(slugParts);
    const gym = await getGymBySlug(slug);

    if (!gym) {
      return {
        title: "ジム詳細 | SPOMAP",
      };
    }

    // Generate optimized title with facility type and sports
    const title = generateSeoTitle(gym);
    const description = generateSeoDescription(gym);

    // Use API route for OG image generation (required for catch-all routes)
    const ogImageUrl = `${baseUrl}/api/og?slug=${encodeURIComponent(slug)}`;

    return {
      title,
      description,
      openGraph: {
        title,
        description,
        type: "website",
        images: [
          {
            url: ogImageUrl,
            width: 1200,
            height: 630,
            alt: `${gym.name} - SPOMAP`,
          },
        ],
      },
      twitter: {
        card: "summary_large_image",
        title,
        description,
        images: [ogImageUrl],
      },
    };
  } catch {
    return {
      title: "ジム詳細 | SPOMAP",
    };
  }
}

import { normalizeGymDetail } from "./normalization";
import { generateBreadcrumbJsonLd } from "./seo";

export default async function GymDetailPage({ params }: PageProps) {
  const { slug: slugParts } = await params;
  const slug = joinSlug(slugParts);
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
    pools: gym.pools,
    court_type: gym.courtType,
    court_count: gym.courtCount,
    court_surface: gym.courtSurface,
    court_lighting: gym.courtLighting,
    courts: gym.courts,
    hall_sports: gym.hallSports,
    hall_area_sqm: gym.hallAreaSqm,
    field_type: gym.fieldType,
    field_count: gym.fieldCount,
    field_lighting: gym.fieldLighting,
    // Archery fields
    archery_type: gym.archeryType,
    archery_rooms: gym.archeryRooms,
    // Categories and official URL
    categories: gym.categories,
    official_url: gym.officialUrl,
  } as any; // Casting to any to avoid strict type matching for now

  const normalized = normalizeGymDetail(apiResponse, gym.slug);

  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || "https://spomap.jp";

  // Structured data for Google rich snippets - SportsActivityLocation
  const sportsLocationJsonLd = {
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
    url: `${baseUrl}/gyms/${gym.slug}`,
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

  // Breadcrumb structured data for search result rich snippets
  const breadcrumbJsonLd = generateBreadcrumbJsonLd(gym, baseUrl);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(sportsLocationJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }}
      />
      <GymDetailClient gym={normalized} />
    </>
  );
}
