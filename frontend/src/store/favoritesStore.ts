"use client";

import { useCallback, useEffect, useMemo } from "react";
import { create } from "zustand";

import {
  addFavorite as apiAddFavorite,
  getFavorites as apiGetFavorites,
  removeFavorite as apiRemoveFavorite,
} from "@/lib/apiClient";
import type { GymDetail, GymSummary } from "@/types/gym";
import type { Favorite } from "@/types/favorite";

const FAVORITES_STORAGE_KEY = "GED_FAVORITES";

const DEFAULT_LOAD_ERROR = "お気に入り一覧の取得に失敗しました。";
const DEFAULT_SYNC_ERROR = "お気に入りの同期に失敗しました。";
const DEFAULT_MUTATION_ERROR = "お気に入りの更新に失敗しました。";

export type FavoritesStatus = "idle" | "loading" | "ready" | "syncing" | "error";

type FavoriteCandidate = GymSummary | GymDetail;

interface FavoritesStoreState {
  favorites: Favorite[];
  pendingIds: number[];
  status: FavoritesStatus;
  error: string | null;
  isInitialized: boolean;
  isAuthenticated: boolean;
  lastSyncedUserId: string | null;
  initialize: () => Promise<void>;
  setAuthenticated: (value: boolean) => void;
  addFavorite: (candidate: FavoriteCandidate) => Promise<void>;
  removeFavorite: (gymId: number) => Promise<void>;
  toggleFavorite: (candidate: FavoriteCandidate) => Promise<void>;
  refreshFromServer: () => Promise<void>;
  syncWithServer: (userId?: string) => Promise<void>;
}

const isBrowser = () => typeof window !== "undefined";

const cloneFavorite = (favorite: Favorite): Favorite => ({
  gym: { ...favorite.gym },
  createdAt: favorite.createdAt ?? null,
});

const dedupeFavorites = (favorites: Favorite[]): Favorite[] => {
  const seen = new Set<number>();
  const result: Favorite[] = [];
  for (const favorite of favorites) {
    if (seen.has(favorite.gym.id)) {
      continue;
    }
    seen.add(favorite.gym.id);
    result.push(cloneFavorite(favorite));
  }
  return result;
};

const candidateToSummary = (candidate: FavoriteCandidate): GymSummary => {
  const summary: GymSummary = {
    id: candidate.id,
    slug: candidate.slug,
    name: candidate.name,
    prefecture: candidate.prefecture,
    city: candidate.city,
    address: candidate.address,
    equipments: "equipments" in candidate ? candidate.equipments : undefined,
    thumbnailUrl: candidate.thumbnailUrl ?? null,
  };

  if ("lastVerifiedAt" in candidate && candidate.lastVerifiedAt !== undefined) {
    summary.lastVerifiedAt = candidate.lastVerifiedAt ?? null;
  }

  return summary;
};

const summaryFromStoredValue = (input: unknown): GymSummary | null => {
  if (!input || typeof input !== "object") {
    return null;
  }

  const value = input as Partial<GymSummary>;
  if (typeof value.id !== "number" || typeof value.slug !== "string" || typeof value.name !== "string") {
    return null;
  }

  return {
    id: value.id,
    slug: value.slug,
    name: value.name,
    prefecture: typeof value.prefecture === "string" ? value.prefecture : "",
    city: typeof value.city === "string" ? value.city : "",
    address: typeof value.address === "string" ? value.address : undefined,
    equipments: Array.isArray(value.equipments) ? value.equipments.map(String) : undefined,
    thumbnailUrl: value.thumbnailUrl ?? null,
    lastVerifiedAt: value.lastVerifiedAt ?? null,
  };
};

const readLocalFavorites = (): Favorite[] => {
  if (!isBrowser()) {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(FAVORITES_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    const summaries = parsed
      .map(summaryFromStoredValue)
      .filter((value): value is GymSummary => value !== null);
    return dedupeFavorites(summaries.map((summary) => ({ gym: summary, createdAt: null })));
  } catch {
    return [];
  }
};

const writeLocalFavorites = (favorites: Favorite[]) => {
  if (!isBrowser()) {
    return;
  }

  try {
    const payload = dedupeFavorites(favorites).map((favorite) => ({ ...favorite.gym }));
    window.localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Ignore storage failures (e.g. private browsing)
  }
};

const removePendingId = (pendingIds: number[], gymId: number) => pendingIds.filter((id) => id !== gymId);

const addPendingId = (pendingIds: number[], gymId: number) =>
  pendingIds.includes(gymId) ? pendingIds : [...pendingIds, gymId];

export const useFavoritesStore = create<FavoritesStoreState>((set, get) => ({
  favorites: [],
  pendingIds: [],
  status: "idle",
  error: null,
  isInitialized: false,
  isAuthenticated: false,
  lastSyncedUserId: null,
  async initialize() {
    if (get().isInitialized) {
      return;
    }
    const favorites = readLocalFavorites();
    set({
      favorites,
      pendingIds: [],
      status: "ready",
      error: null,
      isInitialized: true,
    });
  },
  setAuthenticated(value) {
    set((state) => ({
      isAuthenticated: value,
      lastSyncedUserId: value ? state.lastSyncedUserId : null,
    }));
  },
  async addFavorite(candidate) {
    await get().initialize();
    const summary = candidateToSummary(candidate);
    const optimistic: Favorite = {
      gym: summary,
      createdAt: new Date().toISOString(),
    };

    const previousFavorites = get().favorites.map(cloneFavorite);
    const previousPending = [...get().pendingIds];

    const nextFavorites = dedupeFavorites([
      optimistic,
      ...previousFavorites.filter((favorite) => favorite.gym.id !== summary.id),
    ]);

    set({
      favorites: nextFavorites,
      pendingIds: addPendingId(previousPending, summary.id),
      status: "ready",
      error: null,
      isInitialized: true,
    });
    writeLocalFavorites(nextFavorites);

    if (!get().isAuthenticated) {
      set((state) => ({ pendingIds: removePendingId(state.pendingIds, summary.id) }));
      return;
    }

    try {
      await apiAddFavorite(summary.id);
      set((state) => ({ pendingIds: removePendingId(state.pendingIds, summary.id) }));
      await get().refreshFromServer();
    } catch (error) {
      set({
        favorites: previousFavorites,
        pendingIds: previousPending,
        status: "ready",
        error:
          error instanceof Error && error.message ? error.message : DEFAULT_MUTATION_ERROR,
        isInitialized: true,
      });
      writeLocalFavorites(previousFavorites);
      throw error;
    }
  },
  async removeFavorite(gymId) {
    await get().initialize();
    const previousFavorites = get().favorites.map(cloneFavorite);
    const previousPending = [...get().pendingIds];

    const nextFavorites = previousFavorites.filter((favorite) => favorite.gym.id !== gymId);

    set({
      favorites: nextFavorites,
      pendingIds: addPendingId(previousPending, gymId),
      status: "ready",
      error: null,
      isInitialized: true,
    });
    writeLocalFavorites(nextFavorites);

    if (!get().isAuthenticated) {
      set((state) => ({ pendingIds: removePendingId(state.pendingIds, gymId) }));
      return;
    }

    try {
      await apiRemoveFavorite(gymId);
      set((state) => ({ pendingIds: removePendingId(state.pendingIds, gymId) }));
      await get().refreshFromServer();
    } catch (error) {
      set({
        favorites: previousFavorites,
        pendingIds: previousPending,
        status: "ready",
        error:
          error instanceof Error && error.message ? error.message : DEFAULT_MUTATION_ERROR,
        isInitialized: true,
      });
      writeLocalFavorites(previousFavorites);
      throw error;
    }
  },
  async toggleFavorite(candidate) {
    const summary = candidateToSummary(candidate);
    const isFavorite = get().favorites.some((favorite) => favorite.gym.id === summary.id);
    if (isFavorite) {
      await get().removeFavorite(summary.id);
    } else {
      await get().addFavorite(summary);
    }
  },
  async refreshFromServer() {
    await get().initialize();
    if (!get().isAuthenticated) {
      return;
    }

    set((state) => ({
      status: state.isInitialized ? "syncing" : "loading",
      error: null,
    }));

    try {
      const response = await apiGetFavorites();
      const favorites = dedupeFavorites(
        (response.items ?? []).map((summary) => ({ gym: summary, createdAt: null })),
      );
      set({
        favorites,
        pendingIds: [],
        status: "ready",
        error: null,
        isInitialized: true,
      });
      writeLocalFavorites(favorites);
    } catch (error) {
      const message =
        error instanceof Error && error.message ? error.message : DEFAULT_LOAD_ERROR;
      set((state) => ({
        status: state.isInitialized ? state.status : "error",
        error: message,
        isInitialized: true,
      }));
      throw error;
    }
  },
  async syncWithServer(userId) {
    await get().initialize();
    if (!get().isAuthenticated) {
      return;
    }

    if (userId && get().lastSyncedUserId === userId) {
      await get().refreshFromServer();
      return;
    }

    set((state) => ({
      status: state.isInitialized ? "syncing" : "loading",
      error: null,
    }));

    try {
      const localFavorites = dedupeFavorites(get().favorites);
      const response = await apiGetFavorites();
      const serverFavorites = dedupeFavorites(
        (response.items ?? []).map((summary) => ({ gym: summary, createdAt: null })),
      );
      const serverIds = new Set(serverFavorites.map((favorite) => favorite.gym.id));
      const toAdd = localFavorites
        .map((favorite) => favorite.gym)
        .filter((summary) => !serverIds.has(summary.id));

      for (const summary of toAdd) {
        await apiAddFavorite(summary.id);
      }

      const finalResponse = await apiGetFavorites();
      const finalFavorites = dedupeFavorites(
        (finalResponse.items ?? []).map((summary) => ({ gym: summary, createdAt: null })),
      );

      set({
        favorites: finalFavorites,
        pendingIds: [],
        status: "ready",
        error: null,
        isInitialized: true,
        lastSyncedUserId: userId ?? get().lastSyncedUserId,
      });
      writeLocalFavorites(finalFavorites);
    } catch (error) {
      const message =
        error instanceof Error && error.message ? error.message : DEFAULT_SYNC_ERROR;
      set((state) => ({
        status: state.isInitialized ? state.status : "error",
        error: message,
        isInitialized: true,
      }));
      throw error;
    }
  },
}));

export const favoritesStore = useFavoritesStore;

export function useFavorites() {
  const favorites = useFavoritesStore((state) => state.favorites);
  const status = useFavoritesStore((state) => state.status);
  const error = useFavoritesStore((state) => state.error);
  const pendingIds = useFavoritesStore((state) => state.pendingIds);
  const isInitialized = useFavoritesStore((state) => state.isInitialized);
  const addFavorite = useFavoritesStore((state) => state.addFavorite);
  const removeFavorite = useFavoritesStore((state) => state.removeFavorite);
  const toggleFavorite = useFavoritesStore((state) => state.toggleFavorite);
  const refresh = useFavoritesStore((state) => state.refreshFromServer);
  const initialize = useFavoritesStore((state) => state.initialize);

  useEffect(() => {
    void initialize();
  }, [initialize]);

  const favoriteIds = useMemo(() => favorites.map((favorite) => favorite.gym.id), [favorites]);
  const pendingSet = useMemo(() => new Set(pendingIds), [pendingIds]);

  const isFavorite = useCallback((gymId: number) => favoriteIds.includes(gymId), [favoriteIds]);
  const isPending = useCallback((gymId: number) => pendingSet.has(gymId), [pendingSet]);

  return {
    favorites,
    favoriteIds,
    status,
    error,
    isInitialized,
    isFavorite,
    isPending,
    addFavorite,
    removeFavorite,
    toggleFavorite,
    refresh,
  };
}

export const resetFavoritesStoreForTests = () => {
  if (process.env.NODE_ENV === "production") {
    return;
  }

  useFavoritesStore.setState({
    favorites: [],
    pendingIds: [],
    status: "idle",
    error: null,
    isInitialized: false,
    isAuthenticated: false,
    lastSyncedUserId: null,
  });

  if (isBrowser()) {
    try {
      window.localStorage.removeItem(FAVORITES_STORAGE_KEY);
    } catch {
      // ignore storage errors in tests
    }
  }
};
