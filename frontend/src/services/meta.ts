import { apiRequest } from "@/lib/apiClient";
import type { CityOption, EquipmentCategoryOption, PrefectureOption } from "@/types/meta";

const formatSlugLabel = (slug: string) =>
  slug
    .split("-")
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");

export async function getPrefectures(): Promise<PrefectureOption[]> {
  const response = await apiRequest<string[]>("/meta/prefectures", { method: "GET" });
  return response
    .filter(value => Boolean(value))
    .map(slug => ({
      value: slug,
      label: formatSlugLabel(slug),
    }));
}

export async function getEquipmentCategories(): Promise<EquipmentCategoryOption[]> {
  const response = await apiRequest<string[]>("/meta/equipment-categories", { method: "GET" });
  return response
    .filter(value => Boolean(value))
    .map(name => ({
      value: name,
      label: name,
    }));
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
    .filter(item => Boolean(item?.city))
    .map(item => ({
      value: item.city,
      label: formatSlugLabel(item.city),
    }));
}
