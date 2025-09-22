"use client";

import { useCallback, useSyncExternalStore } from "react";

type FavoriteStoreState = {
  ids: Set<number>;
  isInitialized: boolean;
};

const STORAGE_KEY = "favoriteGymIds";

let state: FavoriteStoreState = {
  ids: new Set<number>(),
  isInitialized: false,
};

let snapshotCache = {
  favoriteGymIds: [] as number[],
  isInitialized: false,
};

const listeners = new Set<() => void>();

const notify = () => {
  listeners.forEach((listener) => listener());
};

const persist = (ids: Set<number>) => {
  if (typeof window === "undefined") {
    return;
  }

  try {
    const serialised = JSON.stringify(Array.from(ids));
    window.localStorage.setItem(STORAGE_KEY, serialised);
  } catch {
    // ignore write failures so the UI remains responsive even in private mode.
  }
};

const setState = (next: FavoriteStoreState, opts: { persist?: boolean; notify?: boolean } = {}) => {
  state = next;
  snapshotCache = {
    favoriteGymIds: Array.from(state.ids),
    isInitialized: state.isInitialized,
  };
  if (opts.persist) {
    persist(state.ids);
  }
  if (opts.notify !== false) {
    notify();
  }
};

const initialiseFromStorage = () => {
  if (state.isInitialized || typeof window === "undefined") {
    return;
  }

  let ids: number[] = [];

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        ids = parsed
          .map((value) => {
            const asNumber = typeof value === "string" ? Number.parseInt(value, 10) : Number(value);
            return Number.isFinite(asNumber) ? asNumber : undefined;
          })
          .filter((value): value is number => typeof value === "number");
      }
    }
  } catch {
    ids = [];
  }

  setState(
    {
      ids: new Set(ids),
      isInitialized: true,
    },
    { notify: true },
  );
};

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

const getSnapshot = () => {
  if (typeof window !== "undefined") {
    initialiseFromStorage();
  }

  return snapshotCache;
};

const getServerSnapshot = () => ({ favoriteGymIds: [] as number[], isInitialized: false });

const addFavoriteIdInternal = (gymId: number) => {
  initialiseFromStorage();
  if (state.ids.has(gymId)) {
    return;
  }

  const nextIds = new Set(state.ids);
  nextIds.add(gymId);

  setState(
    {
      ids: nextIds,
      isInitialized: true,
    },
    { persist: true },
  );
};

const removeFavoriteIdInternal = (gymId: number) => {
  initialiseFromStorage();
  if (!state.ids.has(gymId)) {
    return;
  }

  const nextIds = new Set(state.ids);
  nextIds.delete(gymId);

  setState(
    {
      ids: nextIds,
      isInitialized: true,
    },
    { persist: true },
  );
};

export function useFavoriteGyms() {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const addFavoriteId = useCallback((gymId: number) => {
    addFavoriteIdInternal(gymId);
  }, []);

  const removeFavoriteId = useCallback((gymId: number) => {
    removeFavoriteIdInternal(gymId);
  }, []);

  const isFavorite = useCallback(
    (gymId: number) => snapshot.favoriteGymIds.includes(gymId),
    [snapshot.favoriteGymIds],
  );

  return {
    favoriteGymIds: snapshot.favoriteGymIds,
    isInitialized: snapshot.isInitialized,
    addFavoriteId,
    removeFavoriteId,
    isFavorite,
  };
}

export function resetFavoriteStoreForTests() {
  if (process.env.NODE_ENV === "production") {
    return;
  }

  state = {
    ids: new Set<number>(),
    isInitialized: false,
  };

  snapshotCache = {
    favoriteGymIds: [],
    isInitialized: false,
  };

  notify();
}
