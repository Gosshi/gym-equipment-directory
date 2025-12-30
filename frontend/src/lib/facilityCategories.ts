export const FACILITY_CATEGORY_LABELS: Record<string, string> = {
  gym: "ジム",
  pool: "プール",
  court: "コート",
  field: "グラウンド",
  hall: "体育館",
  martial_arts: "武道場",
  archery: "弓道場",
  facility: "施設",
};

export const FACILITY_CATEGORY_COLORS: Record<string, string> = {
  gym: "bg-emerald-500",
  pool: "bg-cyan-500",
  court: "bg-amber-500",
  field: "bg-orange-500",
  hall: "bg-violet-500",
  martial_arts: "bg-red-500",
  archery: "bg-teal-500",
  facility: "bg-slate-500",
};

const EXCLUDED_CATEGORIES = new Set(["all"]);

export const FACILITY_CATEGORY_OPTIONS = Object.entries(FACILITY_CATEGORY_LABELS)
  .filter(([key]) => key !== "facility")
  .map(([value, label]) => ({ value, label }));

export const normalizeFacilityCategories = (
  categories: string[] | null | undefined,
  fallback: string | null | undefined,
): string[] => {
  const filtered =
    categories?.map(category => category.trim()).filter(category => category.length > 0) ?? [];
  const cleaned = filtered.filter(category => !EXCLUDED_CATEGORIES.has(category));
  if (cleaned.length > 0) {
    return Array.from(new Set(cleaned));
  }
  if (fallback && !EXCLUDED_CATEGORIES.has(fallback)) {
    return [fallback];
  }
  return ["facility"];
};

export const getFacilityCategoryLabel = (category: string | null | undefined): string => {
  if (!category) return "";
  return FACILITY_CATEGORY_LABELS[category] ?? category;
};

export const getFacilityCategoryColorClass = (category: string | null | undefined): string => {
  if (!category) return "bg-muted";
  return FACILITY_CATEGORY_COLORS[category] ?? "bg-muted";
};
