"use client";

import { useCallback, useEffect, useMemo } from "react";
import { useSyncExternalStore } from "react";

import { ensureDeviceId, resetDeviceIdForTests } from "@/lib/deviceId";
import { addFavorite, listFavorites, removeFavorite } from "@/services/favorites";
import type { Favorite } from "@/types/favorite";
import type { GymDetail, GymSummary } from "@/types/gym";

type FavoritesStatus = "idle" | "loading" | "ready" | "syncing" | "error";

type FavoritesState = {
  favorites: Favorite[];
  pending: Set<number>;
  status: FavoritesStatus;
  error: string | null;
  isHydrated: boolean;
};

type FavoritesSnapshot = {
  favorites: Favorite[];
  favoriteIds: number[];
  pendingIds: number[];
  status: FavoritesStatus;
  error: string | null;
  isInitialized: boolean;
};

type FavoriteCandidate = GymSummary | GymDetail;

const DEFAULT_LOAD_ERROR = "お気に入り一覧の取得に失敗しました。";
const DEFAULT_MUTATION_ERROR = "お気に入りの更新に失敗しました。";

let state: FavoritesState = {
  favorites: [],
  pending: new Set<number>(),
  status: "idle",
  error: null,
  isHydrated: false,
};

let snapshotCache: FavoritesSnapshot = {
  favorites: [],
  favoriteIds: [],
  pendingIds: [],
  status: "idle",
  error: null,
  isInitialized: false,
};

const listeners = new Set<() => void>();
let inflightLoad: Promise<void> | null = null;

const cloneFavorite = (input: Favorite): Favorite => ({
  createdAt: input.createdAt,
  gym: { ...input.gym },
});

const buildSnapshot = (current: FavoritesState): FavoritesSnapshot => ({
  favorites: current.favorites.map(cloneFavorite),
  favoriteIds: current.favorites.map((favorite) => favorite.gym.id),
  pendingIds: Array.from(current.pending),
  status: current.status,
  error: current.error,
  isInitialized: current.isHydrated,
});

const notify = () => {
  listeners.forEach((listener) => listener());
};

const setState = (updater: (prev: FavoritesState) => FavoritesState) => {
  state = updater(state);
  snapshotCache = buildSnapshot(state);
  notify();
};

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

const getSnapshot = () => snapshotCache;
const getServerSnapshot = () => snapshotCache;

const toFavoriteSummary = (gym: FavoriteCandidate): GymSummary => ({
  id: gym.id,
  slug: gym.slug,
  name: gym.name,
  prefecture: gym.prefecture,
  city: gym.city,
  address: gym.address,
  thumbnailUrl: gym.thumbnailUrl ?? null,
  equipments: "equipments" in gym ? gym.equipments : undefined,
  lastVerifiedAt: "lastVerifiedAt" in gym ? gym.lastVerifiedAt ?? null : undefined,
});

const loadFavorites = async (deviceId: string, { force = false } = {}) => {
  if (!deviceId) {
    return;
  }

  if (inflightLoad && !force) {
    return inflightLoad;
  }

  if (state.isHydrated && state.status === "ready" && !force) {
    return;
  }

  setState((prev) => ({
    favorites: prev.favorites,
    pending: new Set(prev.pending),
    status: prev.isHydrated ? "syncing" : "loading",
    error: null,
    isHydrated: prev.isHydrated,
  }));

  inflightLoad = listFavorites(deviceId)
    .then((favorites) => {
      setState((prev) => ({
        favorites,
        pending: new Set(prev.pending),
        status: "ready",
        error: null,
        isHydrated: true,
      }));
    })
    .catch((error) => {
      const message = error instanceof Error && error.message ? error.message : DEFAULT_LOAD_ERROR;
      setState((prev) => ({
        favorites: prev.favorites,
        pending: new Set(prev.pending),
        status: prev.isHydrated ? prev.status : "error",
        error: message,
        isHydrated: true,
      }));
      throw error;
    })
    .finally(() => {
      inflightLoad = null;
    });

  return inflightLoad;
};

const addFavoriteInternal = async (candidate: FavoriteCandidate) => {
  const deviceId = ensureDeviceId();
  if (!deviceId) {
    throw new Error("デバイスIDの初期化に失敗しました。");
  }

  const summary = toFavoriteSummary(candidate);
  const optimistic: Favorite = {
    gym: summary,
    createdAt: new Date().toISOString(),
  };

  const previousFavorites = state.favorites.map(cloneFavorite);
  const previousPending = new Set(state.pending);

  setState((prev) => {
    const nextFavorites = prev.favorites.filter((item) => item.gym.id !== summary.id);
    nextFavorites.unshift(optimistic);
    const nextPending = new Set(prev.pending);
    nextPending.add(summary.id);

    return {
      favorites: nextFavorites,
      pending: nextPending,
      status: prev.status === "idle" ? "ready" : prev.status,
      error: null,
      isHydrated: true,
    };
  });

  try {
    await addFavorite(summary.id, deviceId);
    setState((prev) => ({
      favorites: prev.favorites,
      pending: (() => {
        const next = new Set(prev.pending);
        next.delete(summary.id);
        return next;
      })(),
      status: prev.status,
      error: prev.error,
      isHydrated: prev.isHydrated,
    }));
    await loadFavorites(deviceId, { force: true });
  } catch (error) {
    setState(() => ({
      favorites: previousFavorites.map(cloneFavorite),
      pending: new Set(previousPending),
      status: "ready",
      error: error instanceof Error && error.message ? error.message : DEFAULT_MUTATION_ERROR,
      isHydrated: true,
    }));
    throw error;
  }
};

const removeFavoriteInternal = async (gymId: number) => {
  const deviceId = ensureDeviceId();
  if (!deviceId) {
    throw new Error("デバイスIDの初期化に失敗しました。");
  }

  const previousFavorites = state.favorites.map(cloneFavorite);
  const previousPending = new Set(state.pending);

  setState((prev) => {
    const nextFavorites = prev.favorites.filter((item) => item.gym.id !== gymId);
    const nextPending = new Set(prev.pending);
    nextPending.add(gymId);

    return {
      favorites: nextFavorites,
      pending: nextPending,
      status: prev.status === "idle" ? "ready" : prev.status,
      error: null,
      isHydrated: true,
    };
  });

  try {
    await removeFavorite(gymId, deviceId);
    setState((prev) => ({
      favorites: prev.favorites,
      pending: (() => {
        const next = new Set(prev.pending);
        next.delete(gymId);
        return next;
      })(),
      status: prev.status,
      error: prev.error,
      isHydrated: prev.isHydrated,
    }));
    await loadFavorites(deviceId, { force: true });
  } catch (error) {
    setState(() => ({
      favorites: previousFavorites.map(cloneFavorite),
      pending: new Set(previousPending),
      status: "ready",
      error: error instanceof Error && error.message ? error.message : DEFAULT_MUTATION_ERROR,
      isHydrated: true,
    }));
    throw error;
  }
};

export function useFavorites() {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    if (!snapshot.isInitialized) {
      const deviceId = ensureDeviceId();
      if (deviceId) {
        void loadFavorites(deviceId);
      }
    }
  }, [snapshot.isInitialized]);

  const pendingSet = useMemo(() => new Set(snapshot.pendingIds), [snapshot.pendingIds]);

  const isFavorite = useCallback(
    (gymId: number) => snapshot.favoriteIds.includes(gymId),
    [snapshot.favoriteIds],
  );

  const isPending = useCallback((gymId: number) => pendingSet.has(gymId), [pendingSet]);

  const add = useCallback((candidate: FavoriteCandidate) => addFavoriteInternal(candidate), []);

  const remove = useCallback((gymId: number) => removeFavoriteInternal(gymId), []);

  const toggle = useCallback(
    (candidate: FavoriteCandidate) => {
      if (isFavorite(candidate.id)) {
        return remove(candidate.id);
      }
      return add(candidate);
    },
    [add, remove, isFavorite],
  );

  const refresh = useCallback(() => {
    const deviceId = ensureDeviceId();
    if (!deviceId) {
      return Promise.resolve();
    }
    return loadFavorites(deviceId, { force: true }) ?? Promise.resolve();
  }, []);

  return {
    favorites: snapshot.favorites,
    favoriteIds: snapshot.favoriteIds,
    status: snapshot.status,
    error: snapshot.error,
    isInitialized: snapshot.isInitialized,
    isFavorite,
    isPending,
    addFavorite: add,
    removeFavorite: remove,
    toggleFavorite: toggle,
    refresh,
  };
}

export function resetFavoriteStoreForTests() {
  if (process.env.NODE_ENV === "production") {
    return;
  }

  state = {
    favorites: [],
    pending: new Set<number>(),
    status: "idle",
    error: null,
    isHydrated: false,
  };
  snapshotCache = buildSnapshot(state);
  inflightLoad = null;
  resetDeviceIdForTests();
  notify();
}
