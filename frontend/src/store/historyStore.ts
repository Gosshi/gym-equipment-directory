"use client";

import { useEffect } from "react";
import { create } from "zustand";

import { addHistory as apiAddHistory, getHistory as apiGetHistory } from "@/lib/apiClient";
import type { GymDetail, GymSummary } from "@/types/gym";

const HISTORY_STORAGE_KEY = "GED_HISTORY";
const HISTORY_LIMIT = 30;

const DEFAULT_HISTORY_ERROR = "閲覧履歴の更新に失敗しました。";

type HistoryCandidate = GymSummary | GymDetail;

type HistoryStatus = "idle" | "ready" | "syncing" | "error";

interface HistoryStoreState {
  items: GymSummary[];
  status: HistoryStatus;
  error: string | null;
  isInitialized: boolean;
  isAuthenticated: boolean;
  lastSyncedUserId: string | null;
  initialize: () => Promise<void>;
  setAuthenticated: (value: boolean) => void;
  add: (candidate: HistoryCandidate) => Promise<void>;
  refreshFromServer: () => Promise<void>;
  syncWithServer: (userId?: string) => Promise<void>;
}

const isBrowser = () => typeof window !== "undefined";

const candidateToSummary = (candidate: HistoryCandidate): GymSummary => {
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
  if (
    typeof value.id !== "number" ||
    typeof value.slug !== "string" ||
    typeof value.name !== "string"
  ) {
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

const dedupeSummaries = (summaries: GymSummary[]): GymSummary[] => {
  const seen = new Set<number>();
  const result: GymSummary[] = [];
  for (const summary of summaries) {
    if (seen.has(summary.id)) {
      continue;
    }
    seen.add(summary.id);
    result.push({ ...summary });
  }
  return result.slice(0, HISTORY_LIMIT);
};

const readLocalHistory = (): GymSummary[] => {
  if (!isBrowser()) {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(HISTORY_STORAGE_KEY);
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
    return dedupeSummaries(summaries);
  } catch {
    return [];
  }
};

const writeLocalHistory = (summaries: GymSummary[]) => {
  if (!isBrowser()) {
    return;
  }

  try {
    const payload = dedupeSummaries(summaries);
    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Ignore storage failures
  }
};

export const useHistoryStore = create<HistoryStoreState>((set, get) => ({
  items: [],
  status: "idle",
  error: null,
  isInitialized: false,
  isAuthenticated: false,
  lastSyncedUserId: null,
  async initialize() {
    if (get().isInitialized) {
      return;
    }
    const items = readLocalHistory();
    set({
      items,
      status: "ready",
      error: null,
      isInitialized: true,
    });
  },
  setAuthenticated(value) {
    set(state => ({
      isAuthenticated: value,
      lastSyncedUserId: value ? state.lastSyncedUserId : null,
    }));
  },
  async add(candidate) {
    await get().initialize();
    const summary = candidateToSummary(candidate);
    const previousItems = get().items.map(item => ({ ...item }));
    const nextItems = dedupeSummaries([summary, ...previousItems]);

    set({
      items: nextItems,
      status: "ready",
      error: null,
      isInitialized: true,
    });
    writeLocalHistory(nextItems);

    if (!get().isAuthenticated) {
      return;
    }

    try {
      await apiAddHistory({ gymId: summary.id });
    } catch (error) {
      set({
        items: previousItems,
        status: "ready",
        error: error instanceof Error && error.message ? error.message : DEFAULT_HISTORY_ERROR,
        isInitialized: true,
      });
      writeLocalHistory(previousItems);
      throw error;
    }
  },
  async refreshFromServer() {
    await get().initialize();
    if (!get().isAuthenticated) {
      return;
    }

    set({ status: "syncing", error: null });

    try {
      const response = await apiGetHistory();
      const items = dedupeSummaries(response.items ?? []);
      set({ items, status: "ready", error: null, isInitialized: true });
      writeLocalHistory(items);
    } catch (error) {
      set({
        status: "error",
        error: error instanceof Error && error.message ? error.message : DEFAULT_HISTORY_ERROR,
        isInitialized: true,
      });
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

    set({ status: "syncing", error: null });

    try {
      const localItems = dedupeSummaries(get().items);
      const response = await apiGetHistory();
      const serverItems = dedupeSummaries(response.items ?? []);
      const serverIds = new Set(serverItems.map(item => item.id));
      const toAdd = localItems.filter(item => !serverIds.has(item.id));

      if (toAdd.length > 0) {
        await apiAddHistory({ gymIds: toAdd.map(item => item.id) });
      }

      const finalResponse = await apiGetHistory();
      const finalItems = dedupeSummaries(finalResponse.items ?? []);

      set({
        items: finalItems,
        status: "ready",
        error: null,
        isInitialized: true,
        lastSyncedUserId: userId ?? get().lastSyncedUserId,
      });
      writeLocalHistory(finalItems);
    } catch (error) {
      set({
        status: "error",
        error: error instanceof Error && error.message ? error.message : DEFAULT_HISTORY_ERROR,
        isInitialized: true,
      });
      throw error;
    }
  },
}));

export const historyStore = useHistoryStore;

export function useHistory() {
  const items = useHistoryStore(state => state.items);
  const status = useHistoryStore(state => state.status);
  const error = useHistoryStore(state => state.error);
  const initialize = useHistoryStore(state => state.initialize);

  useEffect(() => {
    void initialize();
  }, [initialize]);

  return {
    items,
    status,
    error,
  };
}

export const resetHistoryStoreForTests = () => {
  if (process.env.NODE_ENV === "production") {
    return;
  }

  useHistoryStore.setState({
    items: [],
    status: "idle",
    error: null,
    isInitialized: false,
    isAuthenticated: false,
    lastSyncedUserId: null,
  });

  if (isBrowser()) {
    try {
      window.localStorage.removeItem(HISTORY_STORAGE_KEY);
    } catch {
      // ignore storage errors in tests
    }
  }
};
