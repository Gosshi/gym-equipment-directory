"use client";

import { create } from "zustand";

import {
  DEFAULT_FILTER_STATE,
  filterStateToQueryString,
  type FilterState,
} from "@/lib/searchParams";

const areCategoriesEqual = (a: string[], b: string[]) => {
  if (a.length !== b.length) {
    return false;
  }
  return a.every((value, index) => value === b[index]);
};

export const areFilterStatesEqual = (a: FilterState, b: FilterState) =>
  a.q === b.q &&
  a.pref === b.pref &&
  a.city === b.city &&
  a.sort === b.sort &&
  a.order === b.order &&
  a.page === b.page &&
  a.limit === b.limit &&
  a.distance === b.distance &&
  a.lat === b.lat &&
  a.lng === b.lng &&
  a.min_lat === b.min_lat &&
  a.max_lat === b.max_lat &&
  a.min_lng === b.min_lng &&
  a.max_lng === b.max_lng &&
  areCategoriesEqual(a.categories, b.categories) &&
  areCategoriesEqual(a.equipments, b.equipments) &&
  areCategoriesEqual(a.conditions, b.conditions);

export type NavigationSource = "initial" | "push" | "pop" | "replace" | "idle";

type SearchStoreState = {
  filters: FilterState;
  queryString: string;
  navigationSource: NavigationSource;
  scrollPositions: Record<string, number>;
  setFilters: (next: FilterState, options?: { queryString?: string; force?: boolean }) => void;
  updateFilters: (
    updater: (prev: FilterState) => FilterState,
    options?: { queryString?: string; force?: boolean },
  ) => void;
  setNavigationSource: (source: NavigationSource) => void;
  saveScrollPosition: (query: string, position: number) => void;
  consumeScrollPosition: (query: string) => number | null;
};

export const useSearchStore = create<SearchStoreState>((set, get) => ({
  filters: DEFAULT_FILTER_STATE,
  queryString: filterStateToQueryString(DEFAULT_FILTER_STATE),
  navigationSource: "initial",
  scrollPositions: {},
  setFilters: (next, options) => {
    set(state => {
      const normalized = {
        ...next,
        categories: [...next.categories],
        equipments: [...next.equipments],
      };
      const nextQuery = options?.queryString ?? filterStateToQueryString(normalized);
      const filtersEqual = areFilterStatesEqual(state.filters, normalized);
      const queryUnchanged = state.queryString === nextQuery;

      if (filtersEqual && queryUnchanged) {
        return state;
      }

      if (filtersEqual) {
        return {
          ...state,
          queryString: nextQuery,
        };
      }

      return {
        ...state,
        filters: normalized,
        queryString: nextQuery,
      };
    });
  },
  updateFilters: (updater, options) => {
    const current = get().filters;
    const updated = updater(current);
    get().setFilters(updated, options);
  },
  setNavigationSource: source => {
    set(state =>
      state.navigationSource === source ? state : { ...state, navigationSource: source },
    );
  },
  saveScrollPosition: (query, position) => {
    if (!query) {
      return;
    }
    set(state => ({
      ...state,
      scrollPositions: { ...state.scrollPositions, [query]: position },
    }));
  },
  consumeScrollPosition: query => {
    if (!query) {
      return null;
    }
    const current = get().scrollPositions[query];
    if (typeof current !== "number") {
      return null;
    }
    set(state => {
      const { [query]: _removed, ...rest } = state.scrollPositions;
      return {
        ...state,
        scrollPositions: rest,
      };
    });
    return current;
  },
}));
