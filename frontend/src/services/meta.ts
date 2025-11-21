import { apiRequest } from "@/lib/apiClient";
import type { CityOption, EquipmentOption, PrefectureOption } from "@/types/meta";

const formatSlugLabel = (slug: unknown) => {
  if (typeof slug !== "string") {
    return null;
  }

  const normalized = slug.trim();
  if (!normalized) {
    return null;
  }

  return normalized
    .split("-")
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

export async function getPrefectures(): Promise<PrefectureOption[]> {
  const response = await apiRequest<string[]>("/meta/prefectures", { method: "GET" });
  return response
    .map(slug => ({
      value: typeof slug === "string" ? slug.trim() : "",
      label: formatSlugLabel(slug),
    }))
    .filter(
      (item): item is PrefectureOption =>
        Boolean(item.value) && item.label !== null,
    );
}

type EquipmentMetaResponse = {
  slug: string;
  name: string;
  category: string | null;
};

export async function getEquipmentOptions(): Promise<EquipmentOption[]> {
  const response = await apiRequest<EquipmentMetaResponse[]>("/meta/equipments", { method: "GET" });
  return response
    .map(item => ({
      value: typeof item.slug === "string" ? item.slug.trim() : "",
      label: item.name ?? item.slug,
      slug: typeof item.slug === "string" ? item.slug.trim() : undefined,
      name: item.name ?? item.slug,
      category: item.category ?? null,
    }))
    .filter(
      (item): item is EquipmentOption =>
        Boolean(item.slug) && Boolean(item.value),
    );
}

type CityResponse = {
  city: string;
  count: number;
};

export async function getCities(prefecture: string): Promise<CityOption[]> {
  const trimmed = prefecture.trim();
  if (!trimmed) {
    return [];
  }

  const response = await apiRequest<CityResponse[]>("/meta/cities", {
    method: "GET",
    query: { pref: trimmed },
  });

  return response
    .map(item => ({
      value: typeof item.city === "string" ? item.city.trim() : "",
      label: formatSlugLabel(item.city),
    }))
    .filter((item): item is CityOption => Boolean(item.value) && item.label !== null);
}
