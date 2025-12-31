"use client";

import { useCallback, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AdminApiError,
  AdminCandidateDetail,
  AdminCandidateItem,
  AdminCandidateListParams,
  AdminCandidateListResponse,
  ApproveResponse,
  approveCandidate,
  approveBulkCandidates,
  getCandidate,
  getScrapeBulkStatus,
  listCandidates,
  patchCandidate,
  rejectBulkCandidates,
  rejectCandidate,
  scrapeBulkCandidates,
} from "@/lib/adminApi";

// Query key helpers ---------------------------------------------------------
const candidateListKey = (params: AdminCandidateListParams) => [
  "admin",
  "candidates",
  "list",
  params,
];
const candidateDetailKey = (id: number) => ["admin", "candidates", "detail", id];

// Error normalization --------------------------------------------------------
export interface NormalizedError {
  message: string;
  status?: number;
  detail?: unknown;
}

const toError = (err: unknown): NormalizedError => {
  if (err instanceof AdminApiError) {
    return { message: err.message || "Admin API error", status: err.status, detail: err.detail };
  }
  if (err instanceof Error) {
    return { message: err.message };
  }
  return { message: "不明なエラーが発生しました" };
};

// useAdminCandidates (list) --------------------------------------------------
export interface UseAdminCandidatesOptions {
  params: AdminCandidateListParams;
  enabled?: boolean;
}

export function useAdminCandidates({ params, enabled = true }: UseAdminCandidatesOptions) {
  const query = useQuery<AdminCandidateListResponse, AdminApiError>({
    queryKey: candidateListKey(params),
    queryFn: () => listCandidates(params),
    enabled,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });

  return {
    items: query.data?.items ?? [],
    nextCursor: query.data?.next_cursor ?? null,
    count: query.data?.count ?? null,
    isLoading: query.isLoading || query.isFetching,
    isInitialLoading: query.isLoading && !query.data,
    error: query.error ? toError(query.error) : null,
    refetch: query.refetch,
  };
}

// useAdminCandidateDetail ----------------------------------------------------
export function useAdminCandidateDetail(id: number, options?: { enabled?: boolean }) {
  const enabled = options?.enabled ?? true;
  const query = useQuery<AdminCandidateDetail, AdminApiError>({
    queryKey: candidateDetailKey(id),
    queryFn: () => getCandidate(id),
    enabled: enabled && Number.isFinite(id) && id > 0,
    staleTime: 15_000,
    refetchOnWindowFocus: false,
  });
  return {
    candidate: query.data ?? null,
    isLoading: query.isLoading || query.isFetching,
    isInitialLoading: query.isLoading && !query.data,
    error: query.error ? toError(query.error) : null,
    refetch: query.refetch,
  };
}

// Mutations (single) ---------------------------------------------------------
export function usePatchCandidate(id: number) {
  const qc = useQueryClient();
  const mutation = useMutation<AdminCandidateItem, AdminApiError, Partial<AdminCandidateItem>>({
    mutationFn: payload =>
      patchCandidate(id, {
        name_raw: payload.name_raw ?? undefined,
        address_raw: payload.address_raw ?? null,
        pref_slug: payload.pref_slug ?? null,
        city_slug: payload.city_slug ?? null,
        latitude: payload.latitude ?? null,
        longitude: payload.longitude ?? null,
        parsed_json: undefined, // explicit: editing parsed_json omitted in this hook
      }),
    onSuccess: data => {
      qc.setQueryData(candidateDetailKey(id), (prev: AdminCandidateDetail | undefined) =>
        prev ? ({ ...prev, ...data } as AdminCandidateDetail) : (data as AdminCandidateDetail),
      );
      qc.invalidateQueries({ queryKey: ["admin", "candidates", "list"] });
    },
  });
  return {
    patch: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error ? toError(mutation.error) : null,
  };
}

export function useApproveCandidate(id: number) {
  const qc = useQueryClient();
  const mutation = useMutation<
    ApproveResponse,
    AdminApiError,
    { dry_run?: boolean; override?: unknown }
  >({
    mutationFn: vars =>
      approveCandidate(id, { dry_run: vars.dry_run, override: vars.override as any }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: candidateDetailKey(id) });
      qc.invalidateQueries({ queryKey: ["admin", "candidates", "list"] });
    },
  });
  return {
    approve: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error ? toError(mutation.error) : null,
    data: mutation.data ?? null,
  };
}

export function useRejectCandidate(id: number) {
  const qc = useQueryClient();
  const mutation = useMutation<AdminCandidateItem, AdminApiError, { reason: string }>({
    mutationFn: vars => rejectCandidate(id, vars.reason),
    onSuccess: data => {
      qc.setQueryData(candidateDetailKey(id), (prev: AdminCandidateDetail | undefined) =>
        prev ? ({ ...prev, ...data } as AdminCandidateDetail) : (data as AdminCandidateDetail),
      );
      qc.invalidateQueries({ queryKey: ["admin", "candidates", "list"] });
    },
  });
  return {
    reject: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error ? toError(mutation.error) : null,
    data: mutation.data ?? null,
  };
}

// Bulk operations ------------------------------------------------------------
export function useBulkApproveCandidates() {
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: (vars: { ids: number[]; dry_run?: boolean; reason?: string }) =>
      approveBulkCandidates(vars.ids, { dry_run: vars.dry_run, reason: vars.reason }),
    onSuccess: (_data, vars) => {
      // Invalidate list queries & each candidate detail touched
      qc.invalidateQueries({ queryKey: ["admin", "candidates", "list"] });
      vars.ids.forEach(id => qc.invalidateQueries({ queryKey: candidateDetailKey(id) }));
    },
  });
  return {
    bulkApprove: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error ? toError(mutation.error) : null,
    data: mutation.data ?? null,
  };
}

export function useBulkRejectCandidates() {
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: (vars: { ids: number[]; reason: string; dry_run?: boolean }) =>
      rejectBulkCandidates(vars.ids, { reason: vars.reason, dry_run: vars.dry_run }),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["admin", "candidates", "list"] });
      vars.ids.forEach(id => qc.invalidateQueries({ queryKey: candidateDetailKey(id) }));
    },
  });
  return {
    bulkReject: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error ? toError(mutation.error) : null,
    data: mutation.data ?? null,
  };
}

export function useBulkScrapeCandidates() {
  const mutation = useMutation({
    mutationFn: (vars: { ids: number[]; dry_run?: boolean }) =>
      scrapeBulkCandidates(vars.ids, { dry_run: vars.dry_run }),
  });
  return {
    bulkScrape: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error ? toError(mutation.error) : null,
    data: mutation.data ?? null,
  };
}

export function useBulkScrapeStatus(jobId: string | null, options?: { enabled?: boolean }) {
  const enabled = (options?.enabled ?? true) && Boolean(jobId);
  const query = useQuery({
    queryKey: ["admin", "candidates", "scrape-bulk", jobId],
    queryFn: () => getScrapeBulkStatus(jobId as string),
    enabled,
    refetchInterval: data => {
      if (!data) return 2000;
      return data.status === "completed" ? false : 2000;
    },
  });
  return {
    job: query.data ?? null,
    isLoading: query.isLoading || query.isFetching,
    error: query.error ? toError(query.error) : null,
  };
}

// Convenience ---------------------------------------------------------------
export function useAdminCandidateHelpers() {
  const qc = useQueryClient();
  const invalidateLists = useCallback(() => {
    qc.invalidateQueries({ queryKey: ["admin", "candidates", "list"] });
  }, [qc]);
  const prefetchCandidate = useCallback(
    async (id: number) => {
      await qc.prefetchQuery({ queryKey: candidateDetailKey(id), queryFn: () => getCandidate(id) });
    },
    [qc],
  );
  return { invalidateLists, prefetchCandidate };
}

// Selector for derived states ------------------------------------------------
export const useAdminListDerived = (response: AdminCandidateListResponse | undefined) => {
  return useMemo(() => {
    if (!response) {
      return { total: null, hasMore: false };
    }
    const total = typeof response.count === "number" ? response.count : response.items.length;
    const hasMore = Boolean(response.next_cursor);
    return { total, hasMore };
  }, [response]);
};
