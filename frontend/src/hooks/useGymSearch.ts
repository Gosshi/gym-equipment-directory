import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { ApiError } from "@/lib/apiClient";
import { searchGyms } from "@/services/gyms";
import { getEquipmentCategories, getPrefectures } from "@/services/meta";
import type { GymSearchMeta, GymSummary } from "@/types/gym";
import type {
  EquipmentCategoryOption,
  PrefectureOption,
} from "@/types/meta";

const DEFAULT_PER_PAGE = 12;
const DEFAULT_DEBOUNCE_MS = 300;
const MAX_PER_PAGE = 50;

export type GymSearchFilters = {
  q: string;
  prefecture: string | null;
  equipments: string[];
  page: number;
  perPage: number;
};

type FormState = {
  q: string;
  prefecture: string;
  equipments: string[];
};

const parsePositiveInt = (value: string | null, fallback: number): number => {
  if (!value) {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }
  return parsed;
};

const parseEquipments = (value: string | null): string[] => {
  if (!value) {
    return [];
  }
  return value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
};

const normalizeEquipments = (values: string[]): string[] => {
  const sanitized = values
    .map((value) => value.trim())
    .filter(Boolean);
  return Array.from(new Set(sanitized));
};

const parseSearchParams = (params: URLSearchParams): GymSearchFilters => {
  const q = params.get("q") ?? "";
  const rawPrefecture = params.get("prefecture");
  const prefecture = rawPrefecture ? rawPrefecture.trim() : null;
  const equipments = parseEquipments(params.get("equipment"));
  const page = parsePositiveInt(params.get("page"), 1);
  const perPage = Math.min(
    parsePositiveInt(params.get("per_page"), DEFAULT_PER_PAGE),
    MAX_PER_PAGE,
  );

  return {
    q,
    prefecture,
    equipments,
    page,
    perPage,
  };
};

const toFormState = (filters: GymSearchFilters): FormState => ({
  q: filters.q,
  prefecture: filters.prefecture ?? "",
  equipments: [...filters.equipments],
});

const toSearchParams = (filters: GymSearchFilters) => {
  const params = new URLSearchParams();

  if (filters.q.trim()) {
    params.set("q", filters.q.trim());
  }
  if (filters.prefecture) {
    params.set("prefecture", filters.prefecture);
  }
  if (filters.equipments.length > 0) {
    params.set("equipment", filters.equipments.join(","));
  }
  if (filters.page > 1) {
    params.set("page", String(filters.page));
  }
  if (filters.perPage !== DEFAULT_PER_PAGE) {
    params.set("per_page", String(filters.perPage));
  }

  return params;
};

const areArraysEqual = (a: string[], b: string[]) => {
  if (a.length !== b.length) {
    return false;
  }
  return a.every((value, index) => value === b[index]);
};

export interface UseGymSearchOptions {
  debounceMs?: number;
}

export interface UseGymSearchResult {
  formState: FormState;
  appliedFilters: GymSearchFilters;
  updateKeyword: (value: string) => void;
  updatePrefecture: (value: string) => void;
  updateEquipments: (values: string[]) => void;
  clearFilters: () => void;
  page: number;
  perPage: number;
  setPage: (page: number) => void;
  setPerPage: (perPage: number) => void;
  items: GymSummary[];
  meta: GymSearchMeta;
  isLoading: boolean;
  isInitialLoading: boolean;
  error: string | null;
  retry: () => void;
  prefectures: PrefectureOption[];
  equipmentCategories: EquipmentCategoryOption[];
  isMetaLoading: boolean;
  metaError: string | null;
  reloadMeta: () => void;
}

export function useGymSearch(
  options: UseGymSearchOptions = {},
): UseGymSearchResult {
  const { debounceMs = DEFAULT_DEBOUNCE_MS } = options;
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const searchParamsKey = searchParams.toString();

  const appliedFilters = useMemo(
    () => parseSearchParams(new URLSearchParams(searchParamsKey)),
    [searchParamsKey],
  );

  const [formState, setFormState] = useState<FormState>(() =>
    toFormState(appliedFilters),
  );

  useEffect(() => {
    const next = toFormState(appliedFilters);
    setFormState((prev) => {
      if (
        prev.q === next.q &&
        prev.prefecture === next.prefecture &&
        areArraysEqual(prev.equipments, next.equipments)
      ) {
        return prev;
      }
      return next;
    });
  }, [appliedFilters]);

  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const cancelPendingDebounce = useCallback(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
  }, []);

  useEffect(() => cancelPendingDebounce, [cancelPendingDebounce]);

  const applyFilters = useCallback(
    (nextFilters: GymSearchFilters) => {
      const params = toSearchParams(nextFilters);
      const nextQuery = params.toString();
      if (nextQuery === searchParamsKey) {
        return;
      }
      const nextUrl = nextQuery ? `${pathname}?${nextQuery}` : pathname;
      router.push(nextUrl, { scroll: false });
    },
    [pathname, router, searchParamsKey],
  );

  const scheduleApply = useCallback(
    (updater: (prev: FormState) => FormState) => {
      setFormState((prev) => {
        const updated = updater(prev);
        const next: FormState = {
          q: updated.q,
          prefecture: updated.prefecture,
          equipments: normalizeEquipments(updated.equipments),
        };

        if (
          prev.q === next.q &&
          prev.prefecture === next.prefecture &&
          areArraysEqual(prev.equipments, next.equipments)
        ) {
          return prev;
        }

        cancelPendingDebounce();
        debounceRef.current = setTimeout(() => {
          applyFilters({
            q: next.q.trim(),
            prefecture: next.prefecture.trim() || null,
            equipments: next.equipments,
            page: 1,
            perPage: appliedFilters.perPage,
          });
        }, debounceMs);

        return next;
      });
    },
    [
      appliedFilters.perPage,
      applyFilters,
      cancelPendingDebounce,
      debounceMs,
    ],
  );

  const updateKeyword = useCallback(
    (value: string) => scheduleApply((prev) => ({ ...prev, q: value })),
    [scheduleApply],
  );

  const updatePrefecture = useCallback(
    (value: string) => scheduleApply((prev) => ({ ...prev, prefecture: value })),
    [scheduleApply],
  );

  const updateEquipments = useCallback(
    (values: string[]) =>
      scheduleApply((prev) => ({
        ...prev,
        equipments: values,
      })),
    [scheduleApply],
  );

  const clearFilters = useCallback(() => {
    cancelPendingDebounce();
    setFormState({ q: "", prefecture: "", equipments: [] });
    applyFilters({
      q: "",
      prefecture: null,
      equipments: [],
      page: 1,
      perPage: appliedFilters.perPage,
    });
  }, [
    appliedFilters.perPage,
    applyFilters,
    cancelPendingDebounce,
  ]);

  const setPage = useCallback(
    (page: number) => {
      const nextPage = Number.isFinite(page) && page > 0 ? Math.trunc(page) : 1;
      cancelPendingDebounce();
      applyFilters({
        ...appliedFilters,
        page: nextPage,
      });
    },
    [appliedFilters, applyFilters, cancelPendingDebounce],
  );

  const setPerPage = useCallback(
    (value: number) => {
      const parsed = Number.isFinite(value) ? Math.trunc(value) : DEFAULT_PER_PAGE;
      const clamped = Math.min(Math.max(parsed, 1), MAX_PER_PAGE);
      cancelPendingDebounce();
      applyFilters({
        ...appliedFilters,
        perPage: clamped,
        page: 1,
      });
    },
    [appliedFilters, applyFilters, cancelPendingDebounce],
  );

  const [items, setItems] = useState<GymSummary[]>([]);
  const [meta, setMeta] = useState<GymSearchMeta>({
    total: 0,
    hasNext: false,
    pageToken: null,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(0);

  const retry = useCallback(() => setRefreshIndex((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    setIsLoading(true);
    setError(null);

    searchGyms(
      {
        q: appliedFilters.q || undefined,
        prefecture: appliedFilters.prefecture || undefined,
        equipments: appliedFilters.equipments,
        page: appliedFilters.page,
        perPage: appliedFilters.perPage,
      },
      { signal: controller.signal },
    )
      .then((response) => {
        if (!active) {
          return;
        }
        setItems(response.items);
        setMeta(response.meta);
        setHasLoadedOnce(true);
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        if (
          err instanceof DOMException &&
          err.name === "AbortError"
        ) {
          return;
        }
        if (err instanceof ApiError) {
          setError(err.message || "ジムの取得に失敗しました");
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("ジムの取得に失敗しました");
        }
      })
      .finally(() => {
        if (!active) {
          return;
        }
        setIsLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [appliedFilters, refreshIndex]);

  const [prefectures, setPrefectures] = useState<PrefectureOption[]>([]);
  const [equipmentCategories, setEquipmentCategories] =
    useState<EquipmentCategoryOption[]>([]);
  const [isMetaLoading, setIsMetaLoading] = useState(false);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [metaReloadIndex, setMetaReloadIndex] = useState(0);

  const reloadMeta = useCallback(
    () => setMetaReloadIndex((value) => value + 1),
    [],
  );

  useEffect(() => {
    let active = true;
    setIsMetaLoading(true);
    setMetaError(null);

    Promise.all([getPrefectures(), getEquipmentCategories()])
      .then(([prefData, equipmentData]) => {
        if (!active) {
          return;
        }
        setPrefectures(prefData);
        setEquipmentCategories(equipmentData);
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        if (err instanceof ApiError) {
          setMetaError(err.message || "検索条件の取得に失敗しました");
        } else if (err instanceof Error) {
          setMetaError(err.message);
        } else {
          setMetaError("検索条件の取得に失敗しました");
        }
      })
      .finally(() => {
        if (!active) {
          return;
        }
        setIsMetaLoading(false);
      });

    return () => {
      active = false;
    };
  }, [metaReloadIndex]);

  const isInitialLoading = isLoading && !hasLoadedOnce;

  return {
    formState,
    appliedFilters,
    updateKeyword,
    updatePrefecture,
    updateEquipments,
    clearFilters,
    page: appliedFilters.page,
    perPage: appliedFilters.perPage,
    setPage,
    setPerPage,
    items,
    meta,
    isLoading,
    isInitialLoading,
    error,
    retry,
    prefectures,
    equipmentCategories,
    isMetaLoading,
    metaError,
    reloadMeta,
  };
}
