import { useCallback, useEffect, useMemo, useRef } from "react";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { planNavigation, type HistoryNavigationMode } from "@/lib/urlNavigation";
import { useMapSelectionStore, type MapInteractionSource } from "@/state/mapSelection";
import type { NearbyGym } from "@/types/gym";

interface UseSelectedGymOptions {
  gyms: NearbyGym[];
  queryKey?: string;
  requiredGymIds?: number[];
}

interface UseSelectedGymResult {
  selectedGymId: number | null;
  selectedGym: NearbyGym | null;
  selectedSlug: string | null;
  lastSelectionSource: MapInteractionSource | null;
  lastSelectionAt: number | null;
  selectGym: (id: number | null, source?: MapInteractionSource) => void;
  clearSelection: () => void;
}

const DEFAULT_QUERY_KEY = "gym";

const toGymId = (raw: string | null): number | null => {
  if (!raw) {
    return null;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) ? parsed : null;
};

export function useSelectedGym({
  gyms,
  queryKey = DEFAULT_QUERY_KEY,
  requiredGymIds,
}: UseSelectedGymOptions): UseSelectedGymResult {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const searchParamsSnapshot = searchParams.toString();

  const selectedGymId = useMapSelectionStore(state => state.selectedId);
  const lastSelectionSource = useMapSelectionStore(state => state.lastSelectionSource);
  const lastSelectionAt = useMapSelectionStore(state => state.lastSelectionAt);
  const setSelectedId = useMapSelectionStore(state => state.setSelected);

  const requiredGymIdsSet = useMemo(() => {
    if (!requiredGymIds || requiredGymIds.length === 0) {
      return null;
    }
    return new Set(requiredGymIds);
  }, [requiredGymIds]);

  const skipUrlToStoreSyncRef = useRef(false);
  const skipStoreToUrlSyncRef = useRef(false);
  const nextNavigationModeRef = useRef<"push" | "replace" | null>(null);
  const lastSyncedIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const nextId = toGymId(params.get(queryKey));

      skipUrlToStoreSyncRef.current = true;
      skipStoreToUrlSyncRef.current = true;
      nextNavigationModeRef.current = null;
      setSelectedId(nextId, "url");
    };

    window.addEventListener("popstate", handlePopState);

    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, [queryKey, setSelectedId]);

  useEffect(() => {
    if (skipUrlToStoreSyncRef.current) {
      skipUrlToStoreSyncRef.current = false;
      return;
    }

    const params = new URLSearchParams(searchParamsSnapshot);
    const nextId = toGymId(params.get(queryKey));

    if (nextId === selectedGymId) {
      return;
    }

    setSelectedId(nextId, "url");
  }, [queryKey, searchParamsSnapshot, selectedGymId, setSelectedId]);

  useEffect(() => {
    if (!pathname) {
      return;
    }

    if (skipStoreToUrlSyncRef.current) {
      skipStoreToUrlSyncRef.current = false;
      lastSyncedIdRef.current = selectedGymId;
      nextNavigationModeRef.current = null;
      return;
    }

    if (selectedGymId === lastSyncedIdRef.current) {
      nextNavigationModeRef.current = null;
      return;
    }

    const params = new URLSearchParams(searchParamsSnapshot);
    const current = params.get(queryKey);
    const next = selectedGymId == null ? null : String(selectedGymId);

    if (next === current) {
      lastSyncedIdRef.current = selectedGymId;
      nextNavigationModeRef.current = null;
      return;
    }

    if (next === null) {
      params.delete(queryKey);
    } else {
      params.set(queryKey, next);
    }

    const nextQuery = params.toString();
    const desiredMode: HistoryNavigationMode =
      nextNavigationModeRef.current ?? (nextQuery === searchParamsSnapshot ? "replace" : "push");
    const plan = planNavigation({
      pathname,
      currentSearch: searchParamsSnapshot,
      nextSearch: nextQuery,
      mode: desiredMode,
    });

    skipUrlToStoreSyncRef.current = plan.shouldNavigate;
    lastSyncedIdRef.current = selectedGymId;
    nextNavigationModeRef.current = null;

    if (!plan.shouldNavigate || !plan.url) {
      return;
    }

    if (plan.mode === "replace") {
      router.replace(plan.url, { scroll: false });
    } else {
      router.push(plan.url, { scroll: false });
    }
  }, [pathname, queryKey, router, searchParamsSnapshot, selectedGymId]);

  useEffect(() => {
    if (selectedGymId === null) {
      return;
    }

    if (requiredGymIdsSet && !requiredGymIdsSet.has(selectedGymId)) {
      skipUrlToStoreSyncRef.current = true;
      skipStoreToUrlSyncRef.current = false;
      nextNavigationModeRef.current = "replace";
      setSelectedId(null);
      return;
    }

    if (gyms.some(gym => gym.id === selectedGymId)) {
      return;
    }

    skipUrlToStoreSyncRef.current = true;
    skipStoreToUrlSyncRef.current = false;
    nextNavigationModeRef.current = "replace";
    setSelectedId(null);
  }, [gyms, requiredGymIdsSet, selectedGymId, setSelectedId]);

  const selectedGym = useMemo(
    () => gyms.find(gym => gym.id === selectedGymId) ?? null,
    [gyms, selectedGymId],
  );

  const selectGym = useCallback(
    (id: number | null, source?: MapInteractionSource) => {
      skipUrlToStoreSyncRef.current = true;
      skipStoreToUrlSyncRef.current = false;
      nextNavigationModeRef.current = "push";
      if (id === selectedGymId) {
        setSelectedId(null, source);
        return;
      }
      setSelectedId(id, source);
    },
    [selectedGymId, setSelectedId],
  );

  const clearSelection = useCallback(() => {
    if (selectedGymId === null) {
      return;
    }
    skipUrlToStoreSyncRef.current = true;
    skipStoreToUrlSyncRef.current = false;
    nextNavigationModeRef.current = "push";
    setSelectedId(null);
  }, [selectedGymId, setSelectedId]);

  return {
    selectedGymId,
    selectedGym,
    selectedSlug: selectedGym?.slug ?? null,
    lastSelectionSource,
    lastSelectionAt,
    selectGym,
    clearSelection,
  };
}
