import { MetadataRoute } from "next";

import { fetchGyms } from "@/lib/api";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || "https://ironmap.app"; // Fallback URL
  const limit = 100;
  const maxPages = 10; // Fetch up to 1000 gyms for now
  let allGyms: { slug: string; lastVerifiedAt?: string }[] = [];

  for (let page = 1; page <= maxPages; page++) {
    try {
      const response = await fetchGyms({
        page,
        limit,
        sort: "freshness", // Prioritize recently updated gyms
      });

      const items = response.items.map(gym => ({
        slug: gym.slug,
        lastVerifiedAt: gym.lastVerifiedAt ?? undefined,
      }));

      allGyms = [...allGyms, ...items];

      if (!response.meta.hasNext) {
        break;
      }
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error(`Failed to fetch gyms for sitemap page ${page}`, error);
      break;
    }
  }

  const gymUrls = allGyms.map(gym => ({
    url: `${baseUrl}/gyms/${gym.slug}`,
    lastModified: gym.lastVerifiedAt ? new Date(gym.lastVerifiedAt) : new Date(),
    changeFrequency: "weekly" as const,
    priority: 0.8,
  }));

  return [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1,
    },
    {
      url: `${baseUrl}/gyms`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.9,
    },
    ...gymUrls,
  ];
}
