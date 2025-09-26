"use client";

import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";

import {
  clampLatitude,
  clampLongitude,
  DEFAULT_DISTANCE_KM,
  DEFAULT_FILTER_STATE,
  DEFAULT_LIMIT,
  MAX_DISTANCE_KM,
  MAX_LIMIT,
  MIN_DISTANCE_KM,
  SORT_OPTIONS,
  SortOption,
  type FilterState,
  type SortOrder,
  normalizeSortOrder,
  parseFilterState,
  serializeFilterState,
} from "@/lib/searchParams";

const DEFAULT_CENTER = Object.freeze({
  lat: 35.681236,
  lng: 139.767125,
});

const DEFAULT_SORT: SortOption = DEFAULT_FILTER_STATE.sort;
const DEFAULT_ORDER_VALUE: SortOrder = DEFAULT_FILTER_STATE.order;
const DEFAULT_LIMIT_VALUE = DEFAULT_LIMIT;
const DEFAULT_RADIUS_KM = DEFAULT_DISTANCE_KM;
const DEFAULT_ZOOM = 12;

const logEvent = (
  type: "page_change" | "filter_change" | "map_move",
  payload: Record<string, unknown>,
) => {
  if (typeof console === "undefined" || typeof console.info !== "function") {
    return;
  }
  console.info(type, payload);
};

const clampRadius = (value: number | null | undefined): number => {
  if (value == null || Number.isNaN(value) || !Number.isFinite(value)) {
    return DEFAULT_DISTANCE_KM;
  }
  const rounded = Math.round(value);
  return Math.min(Math.max(rounded, MIN_DISTANCE_KM), MAX_DISTANCE_KM);
};

const clampPage = (value: number | null | undefined): number => {
  if (value == null || Number.isNaN(value) || !Number.isFinite(value)) {
    return 1;
  }
  const parsed = Math.trunc(value);
  return parsed > 0 ? parsed : 1;
};

const clampLimit = (value: number | null | undefined): number => {
  if (value == null || Number.isNaN(value) || !Number.isFinite(value)) {
    return DEFAULT_LIMIT_VALUE;
  }
  const parsed = Math.trunc(value);
  if (parsed <= 0) {
    return DEFAULT_LIMIT_VALUE;
  }
  return Math.min(parsed, MAX_LIMIT);
};

const sanitizeSort = (value: string | null | undefined): SortOption => {
  if (!value) {
    return DEFAULT_SORT;
  }
  const normalized = value.trim().toLowerCase();
  const match = SORT_OPTIONS.find(option => option === normalized);
  return match ?? DEFAULT_SORT;
};

const parseQueryParams = (params: URLSearchParams): ParsedQueryParams => {
  const parsed = parseFilterState(params);
  return {
    q: parsed.q,
    prefecture: parsed.pref ?? "",
    city: parsed.city ?? "",
    categories: parsed.categories,
    sort: parsed.sort,
    order: parsed.order,
    lat: parsed.lat,
    lng: parsed.lng,
    radiusKm: clampRadius(parsed.distance),
    page: clampPage(parsed.page),
    limit: clampLimit(parsed.limit),
  };
};

const toFilterState = (state: GymSearchStoreState): FilterState => ({
  q: state.q,
  pref: state.prefecture ? state.prefecture : null,
  city: state.city ? state.city : null,
  categories: [...state.categories],
  sort: state.sort,
  order: normalizeSortOrder(state.sort, state.order),
  page: state.page,
  limit: state.limit,
  distance: state.radiusKm,
  lat: state.lat,
  lng: state.lng,
});

const buildSearchParams = (state: GymSearchStoreState): URLSearchParams =>
  serializeFilterState(toFilterState(state));

type HistoryMode = "replace" | "push";

type BusyFlags = {
  hydrating: boolean;
  urlSync: boolean;
  mapInteracting: boolean;
};

type ParsedQueryParams = {
  q: string;
  prefecture: string;
  city: string;
  categories: string[];
  sort: SortOption;
  order: SortOrder;
  lat: number | null;
  lng: number | null;
  radiusKm: number;
  page: number;
  limit: number;
};

type GymSearchStoreState = {
  q: string;
  prefecture: string;
  city: string;
  categories: string[];
  lat: number | null;
  lng: number | null;
  radiusKm: number;
  page: number;
  limit: number;
  sort: SortOption;
  order: SortOrder;
  zoom: number;
  selectedGymSlug: string | null;
  selectedGymId: number | null;
  lastSelectionSource: "map" | "list" | "panel" | "url" | null;
  lastSelectionAt: number | null;
  rightPanelOpen: boolean;
  busyFlags: BusyFlags;
  hydrated: boolean;
  pendingHistory: HistoryMode;
  lastSyncedQuery: string;
};

type GymSearchStoreActions = {
  hydrateFromUrl: (url: URL | string) => void;
  applyUrlState: (url: URL | string) => void;
  markUrlSynced: (query: string) => void;
  setQuery: (value: string) => void;
  setPrefecture: (value: string) => void;
  setCity: (value: string) => void;
  setCategories: (values: string[]) => void;
  setSort: (sort: SortOption, order?: SortOrder) => void;
  setDistance: (distance: number) => void;
  setMapState: (input: { lat: number; lng: number; radiusKm?: number; zoom?: number }) => void;
  setPagination: (page: number, options?: { history?: HistoryMode }) => void;
  setLimit: (limit: number) => void;
  setLocation: (payload: { lat: number | null; lng: number | null }) => void;
  setSelectedGym: (payload: {
    slug: string | null;
    id: number | null;
    source?: "map" | "list" | "panel" | "url";
  }) => void;
  setRightPanelOpen: (open: boolean) => void;
  resetFilters: () => void;
  resetSelectionIfMissing: (availableSlugs: Set<string>) => void;
  setTotalPages: (totalPages: number | null) => void;
  setBusyFlag: (key: keyof BusyFlags, value: boolean) => void;
};

type GymSearchStore = GymSearchStoreState & GymSearchStoreActions;

const INITIAL_STATE: GymSearchStoreState = {
  q: "",
  prefecture: "",
  city: "",
  categories: [],
  lat: DEFAULT_FILTER_STATE.lat ?? DEFAULT_CENTER.lat,
  lng: DEFAULT_FILTER_STATE.lng ?? DEFAULT_CENTER.lng,
  radiusKm: DEFAULT_RADIUS_KM,
  page: 1,
  limit: DEFAULT_LIMIT_VALUE,
  sort: DEFAULT_SORT,
  order: DEFAULT_ORDER_VALUE,
  zoom: DEFAULT_ZOOM,
  selectedGymSlug: null,
  selectedGymId: null,
  lastSelectionSource: null,
  lastSelectionAt: null,
  rightPanelOpen: false,
  busyFlags: {
    hydrating: false,
    urlSync: false,
    mapInteracting: false,
  },
  hydrated: false,
  pendingHistory: "replace",
  lastSyncedQuery: "",
};

export const useGymSearchStore = create<GymSearchStore>()(
  subscribeWithSelector((set, get) => ({
    ...INITIAL_STATE,
    hydrateFromUrl: input => {
      const url = typeof input === "string" ? new URL(input, "http://localhost") : input;
      const params = url.searchParams;
      const parsed = parseQueryParams(params);
      set({
        ...parsed,
        zoom: get().zoom,
        selectedGymSlug: get().selectedGymSlug,
        selectedGymId: get().selectedGymId,
        busyFlags: { ...get().busyFlags, hydrating: true },
        hydrated: true,
        pendingHistory: "replace",
      });
      set(state => ({
        busyFlags: { ...state.busyFlags, hydrating: false },
        lastSyncedQuery: buildSearchParams(state).toString(),
      }));
    },
    applyUrlState: input => {
      const url = typeof input === "string" ? new URL(input, "http://localhost") : input;
      const params = url.searchParams;
      const parsed = parseQueryParams(params);
      set(state => ({
        ...state,
        ...parsed,
        busyFlags: { ...state.busyFlags, urlSync: true },
        pendingHistory: "replace",
        hydrated: true,
      }));
      set(state => ({
        busyFlags: { ...state.busyFlags, urlSync: false },
        lastSyncedQuery: buildSearchParams(state).toString(),
      }));
    },
    markUrlSynced: query => {
      set(state => ({
        pendingHistory: "replace",
        lastSyncedQuery: query,
      }));
    },
    setQuery: value => {
      const next = value ?? "";
      set(state => ({
        q: next,
        page: 1,
        pendingHistory: "replace",
      }));
      logEvent("filter_change", { filter: "q", value: next });
    },
    setPrefecture: value => {
      const next = typeof value === "string" ? value.trim() : "";
      set(state => ({
        prefecture: next,
        city: "",
        page: 1,
        pendingHistory: "replace",
      }));
      logEvent("filter_change", { filter: "prefecture", value: next });
    },
    setCity: value => {
      const next = typeof value === "string" ? value.trim() : "";
      set(state => ({
        city: next,
        page: 1,
        pendingHistory: "replace",
      }));
      logEvent("filter_change", { filter: "city", value: next });
    },
    setCategories: values => {
      const normalized = Array.from(
        new Set((values ?? []).map(item => item.trim()).filter(Boolean)),
      );
      set(state => ({
        categories: normalized,
        page: 1,
        pendingHistory: "replace",
      }));
      logEvent("filter_change", { filter: "categories", value: normalized });
    },
    setSort: (sort, order) => {
      const next = sanitizeSort(sort);
      const nextOrder = normalizeSortOrder(next, order ?? DEFAULT_ORDER_VALUE);
      set(state => ({
        sort: next,
        order: nextOrder,
        page: 1,
        pendingHistory: "replace",
      }));
      logEvent("filter_change", { filter: "sort", value: next, order: nextOrder });
    },
    setDistance: distance => {
      const next = clampRadius(distance);
      set(state => ({
        radiusKm: next,
        page: 1,
        pendingHistory: "replace",
      }));
      logEvent("filter_change", { filter: "distance", value: next });
    },
    setMapState: ({ lat, lng, radiusKm, zoom }) => {
      const sanitizedLat = clampLatitude(lat);
      const sanitizedLng = clampLongitude(lng);
      const sanitizedRadius = radiusKm != null ? clampRadius(radiusKm) : undefined;
      const sanitizedZoom = zoom != null && Number.isFinite(zoom) ? zoom : undefined;
      set(state => ({
        lat: sanitizedLat,
        lng: sanitizedLng,
        radiusKm: sanitizedRadius ?? state.radiusKm,
        zoom: sanitizedZoom ?? state.zoom,
        page: 1,
        pendingHistory: "replace",
      }));
      const state = get();
      logEvent("map_move", {
        lat: sanitizedLat,
        lng: sanitizedLng,
        radiusKm: sanitizedRadius ?? state.radiusKm,
        zoom: sanitizedZoom ?? state.zoom,
      });
    },
    setPagination: (page, options) => {
      const nextPage = clampPage(page);
      set(state => ({
        page: nextPage,
        pendingHistory: options?.history ?? "push",
      }));
      logEvent("page_change", { page: nextPage });
    },
    setLimit: limit => {
      const sanitized = clampLimit(limit);
      set(state => ({
        limit: sanitized,
        page: 1,
        pendingHistory: "replace",
      }));
      logEvent("filter_change", { filter: "limit", value: sanitized });
    },
    setLocation: ({ lat, lng }) => {
      const sanitizedLat = lat == null ? null : clampLatitude(lat);
      const sanitizedLng = lng == null ? null : clampLongitude(lng);
      set(state => ({
        lat: sanitizedLat,
        lng: sanitizedLng,
        page: 1,
        pendingHistory: "replace",
      }));
      logEvent("filter_change", { filter: "location", lat: sanitizedLat, lng: sanitizedLng });
    },
    setSelectedGym: ({ slug, id, source }) => {
      set(state => ({
        selectedGymSlug: slug ?? null,
        selectedGymId: id ?? null,
        rightPanelOpen: slug != null,
        lastSelectionSource: source ?? state.lastSelectionSource,
        lastSelectionAt: source ? Date.now() : state.lastSelectionAt,
      }));
    },
    setRightPanelOpen: open => {
      set(state => ({
        rightPanelOpen: open,
        pendingHistory: "replace",
      }));
    },
    resetFilters: () => {
      set(state => ({
        q: "",
        prefecture: "",
        city: "",
        categories: [],
        sort: DEFAULT_SORT,
        order: DEFAULT_ORDER_VALUE,
        lat: DEFAULT_FILTER_STATE.lat ?? DEFAULT_CENTER.lat,
        lng: DEFAULT_FILTER_STATE.lng ?? DEFAULT_CENTER.lng,
        radiusKm: DEFAULT_RADIUS_KM,
        limit: DEFAULT_LIMIT_VALUE,
        page: 1,
        pendingHistory: "replace",
      }));
      logEvent("filter_change", { filter: "reset" });
    },
    resetSelectionIfMissing: availableSlugs => {
      set(state => {
        if (!state.selectedGymSlug) {
          return state;
        }
        if (availableSlugs.has(state.selectedGymSlug)) {
          return state;
        }
        return {
          ...state,
          selectedGymSlug: null,
          selectedGymId: null,
          rightPanelOpen: false,
          lastSelectionSource: null,
          lastSelectionAt: null,
        };
      });
    },
    setTotalPages: totalPages => {
      if (totalPages == null || !Number.isFinite(totalPages)) {
        return;
      }
      set(state => {
        const maxPage = Math.max(1, Math.trunc(totalPages));
        if (state.page <= maxPage) {
          return state;
        }
        return {
          ...state,
          page: maxPage,
          pendingHistory: "replace",
        };
      });
    },
    setBusyFlag: (key, value) => {
      set(state => ({
        busyFlags: {
          ...state.busyFlags,
          [key]: value,
        },
      }));
    },
  })),
);

export const gymSearchStore = useGymSearchStore;

export const buildSearchQueryString = (state: GymSearchStoreState): string =>
  buildSearchParams(state).toString();

export type { GymSearchStoreState };
