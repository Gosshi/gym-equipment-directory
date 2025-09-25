import { useCallback, useEffect, useMemo, useRef } from "react";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { useMapSelectionStore, type MapInteractionSource } from "@/state/mapSelection";
import type { NearbyGym } from "@/types/gym";

interface UseSelectedGymOptions {
  gyms: NearbyGym[];
  queryKey?: string;
}

interface UseSelectedGymResult {
  selectedGymId: number | null;
  selectedGym: NearbyGym | null;
  selectedSlug: string | null;
  hoveredGymId: number | null;
  lastSelectionSource: MapInteractionSource | null;
  lastSelectionAt: number | null;
  selectGym: (id: number | null, source?: MapInteractionSource) => void;
  previewGym: (id: number | null, source?: MapInteractionSource) => void;
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
}: UseSelectedGymOptions): UseSelectedGymResult {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const searchParamsSnapshot = searchParams.toString();

  const selectedGymId = useMapSelectionStore(state => state.selectedId);
  const hoveredGymId = useMapSelectionStore(state => state.hoveredId);
  const lastSelectionSource = useMapSelectionStore(state => state.lastSelectionSource);
  const lastSelectionAt = useMapSelectionStore(state => state.lastSelectionAt);
  const setSelectedId = useMapSelectionStore(state => state.setSelected);
  const setHoveredId = useMapSelectionStore(state => state.setHovered);

  const skipUrlToStoreSyncRef = useRef(false);
  const lastSyncedIdRef = useRef<number | null>(null);

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

    if (selectedGymId === lastSyncedIdRef.current) {
      return;
    }

    const params = new URLSearchParams(searchParamsSnapshot);
    const current = params.get(queryKey);
    const next = selectedGymId == null ? null : String(selectedGymId);

    if (next === current) {
      lastSyncedIdRef.current = selectedGymId;
      return;
    }

    if (next === null) {
      params.delete(queryKey);
    } else {
      params.set(queryKey, next);
    }

    const query = params.toString();
    const url = query ? `${pathname}?${query}` : pathname;

    skipUrlToStoreSyncRef.current = true;
    lastSyncedIdRef.current = selectedGymId;
    router.replace(url, { scroll: false });
  }, [pathname, queryKey, router, searchParamsSnapshot, selectedGymId]);

  useEffect(() => {
    if (selectedGymId === null) {
      return;
    }

    if (gyms.some(gym => gym.id === selectedGymId)) {
      return;
    }

    skipUrlToStoreSyncRef.current = true;
    setSelectedId(null);
  }, [gyms, selectedGymId, setSelectedId]);

  const selectedGym = useMemo(
    () => gyms.find(gym => gym.id === selectedGymId) ?? null,
    [gyms, selectedGymId],
  );

  const selectGym = useCallback(
    (id: number | null, source?: MapInteractionSource) => {
      if (id === selectedGymId) {
        if (id !== null) {
          setHoveredId(null);
        }
        return;
      }
      skipUrlToStoreSyncRef.current = true;
      setSelectedId(id, source);
      if (id !== null) {
        setHoveredId(null);
      }
    },
    [selectedGymId, setHoveredId, setSelectedId],
  );

  const previewGym = useCallback(
    (id: number | null, source?: MapInteractionSource) => {
      setHoveredId(id, source);
    },
    [setHoveredId],
  );

  const clearSelection = useCallback(() => {
    if (selectedGymId === null) {
      return;
    }
    skipUrlToStoreSyncRef.current = true;
    setSelectedId(null);
  }, [selectedGymId, setSelectedId]);

  return {
    selectedGymId,
    selectedGym,
    selectedSlug: selectedGym?.slug ?? null,
    hoveredGymId,
    lastSelectionSource,
    lastSelectionAt,
    selectGym,
    previewGym,
    clearSelection,
  };
}
