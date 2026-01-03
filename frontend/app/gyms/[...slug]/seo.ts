/**
 * SEO helpers for gym detail pages.
 * Generates optimized titles, descriptions, and structured data.
 */

import type { GymDetail } from "@/types/gym";

/**
 * Category display names for Japanese users.
 */
const CATEGORY_LABELS: Record<string, string> = {
  gym: "トレーニングルーム",
  pool: "プール",
  court: "コート",
  hall: "体育館",
  field: "グラウンド",
  martial_arts: "武道場",
  archery: "弓道場",
};

/**
 * Equipment-to-sport name mapping for title optimization.
 * Maps equipment names to user-friendly sport names.
 */
const EQUIPMENT_TO_SPORT: Record<string, string> = {
  // Table tennis
  卓球台: "卓球",
  卓球: "卓球",
  // Basketball
  バスケットゴール: "バスケ",
  バスケットボール: "バスケ",
  バスケ: "バスケ",
  // Volleyball
  バレーボール: "バレー",
  バレー: "バレー",
  // Badminton
  バドミントン: "バドミントン",
  // Swimming
  プール: "水泳",
  競泳: "水泳",
  水深: "水泳",
  // Training
  トレーニングルーム: "トレーニング",
  トレーニング: "トレーニング",
  ジム: "トレーニング",
  ウェイト: "トレーニング",
  マシン: "トレーニング",
  // Tennis
  テニスコート: "テニス",
  テニス: "テニス",
  // Futsal/Soccer
  フットサル: "フットサル",
  サッカー: "サッカー",
  // Martial arts
  柔道場: "柔道",
  剣道場: "剣道",
  武道場: "武道",
  // Archery
  弓道場: "弓道",
  アーチェリー: "アーチェリー",
};

/**
 * Extract sport names from gym data.
 * Prioritizes hallSports, then extracts from equipments using dictionary.
 */
export function extractSportNames(gym: GymDetail): string[] {
  const sports = new Set<string>();

  // 1. Use hallSports if available (already curated sport names)
  if (gym.hallSports && gym.hallSports.length > 0) {
    for (const sport of gym.hallSports) {
      sports.add(sport);
    }
  }

  // 2. Extract from equipments using dictionary mapping
  if (gym.equipments && gym.equipments.length > 0) {
    for (const equipment of gym.equipments) {
      // Direct match
      if (EQUIPMENT_TO_SPORT[equipment]) {
        sports.add(EQUIPMENT_TO_SPORT[equipment]);
        continue;
      }
      // Partial match (e.g., "卓球台（2台）" matches "卓球台")
      for (const [key, value] of Object.entries(EQUIPMENT_TO_SPORT)) {
        if (equipment.includes(key)) {
          sports.add(value);
          break;
        }
      }
    }
  }

  // 3. Infer from category if no sports found
  if (sports.size === 0 && gym.category) {
    if (gym.category === "pool") sports.add("水泳");
    if (gym.category === "archery") sports.add("弓道");
  }

  return Array.from(sports);
}

/**
 * Get the primary facility type label for the gym.
 */
export function getFacilityTypeLabel(gym: GymDetail): string | null {
  // Prioritize primary category
  if (gym.category && CATEGORY_LABELS[gym.category]) {
    return CATEGORY_LABELS[gym.category];
  }

  // Check categories array
  if (gym.categories && gym.categories.length > 0) {
    for (const cat of gym.categories) {
      if (CATEGORY_LABELS[cat]) {
        return CATEGORY_LABELS[cat];
      }
    }
  }

  return null;
}

/**
 * Generate an optimized page title for SEO.
 * Format: "施設名（施設タイプ・競技1・競技2） | 市区町村 | SPOMAP"
 */
export function generateSeoTitle(gym: GymDetail): string {
  const parts: string[] = [];

  // Facility type
  const facilityType = getFacilityTypeLabel(gym);
  if (facilityType) {
    parts.push(facilityType);
  }

  // Sports (max 2 to keep title concise)
  const sports = extractSportNames(gym).slice(0, 2);
  parts.push(...sports);

  // Remove duplicates (e.g., if facilityType is already in sports)
  const uniqueParts = [...new Set(parts)].slice(0, 3);

  // Build title
  let title = gym.name;
  if (uniqueParts.length > 0) {
    title += `（${uniqueParts.join("・")}）`;
  }

  // Add location
  const location = gym.city || gym.prefecture;
  if (location) {
    title += ` | ${location}`;
  }

  title += " | SPOMAP";

  return title;
}

/**
 * Breadcrumb item for JSON-LD.
 */
interface BreadcrumbItem {
  name: string;
  url: string;
}

/**
 * Generate breadcrumb list for JSON-LD structured data.
 * Hierarchy: ホーム > 施設検索 > 都道府県 > 市区町村 > 施設名
 */
export function generateBreadcrumbItems(gym: GymDetail, baseUrl: string): BreadcrumbItem[] {
  const items: BreadcrumbItem[] = [
    { name: "ホーム", url: baseUrl },
    { name: "施設検索", url: `${baseUrl}/gyms` },
  ];

  // Prefecture level
  if (gym.prefecture) {
    items.push({
      name: gym.prefecture,
      url: `${baseUrl}/gyms?pref=${encodeURIComponent(gym.prefecture)}`,
    });
  }

  // City level
  if (gym.city && gym.prefecture) {
    items.push({
      name: gym.city,
      url: `${baseUrl}/gyms?pref=${encodeURIComponent(gym.prefecture)}&city=${encodeURIComponent(gym.city)}`,
    });
  }

  // Current page (facility name)
  items.push({
    name: gym.name,
    url: `${baseUrl}/gyms/${gym.slug}`,
  });

  return items;
}

/**
 * Generate BreadcrumbList JSON-LD structured data.
 */
export function generateBreadcrumbJsonLd(gym: GymDetail, baseUrl: string): object {
  const items = generateBreadcrumbItems(gym, baseUrl);

  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: item.url,
    })),
  };
}

/**
 * Generate an optimized meta description for SEO.
 */
export function generateSeoDescription(gym: GymDetail): string {
  const location = `${gym.prefecture ?? ""}${gym.city ?? ""}`;
  const facilityType = getFacilityTypeLabel(gym);
  const sports = extractSportNames(gym).slice(0, 3);

  let description = "";

  if (location) {
    description += `${location}にある`;
  }

  if (facilityType) {
    description += `「${gym.name}」（${facilityType}）`;
  } else {
    description += `「${gym.name}」`;
  }

  description += "の設備情報。";

  if (sports.length > 0) {
    description += `${sports.join("・")}などが利用可能。`;
  }

  if (gym.equipments && gym.equipments.length > 0) {
    const equipmentList = gym.equipments.slice(0, 5).join("、");
    description += `主な設備: ${equipmentList}。`;
  }

  return description;
}
