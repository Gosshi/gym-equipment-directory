"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import type { AdminCandidateListParams } from "@/lib/adminApi";
import { toast } from "@/components/ui/use-toast";
import {
  useAdminCandidates,
  useBulkApproveCandidates,
  useBulkRejectCandidates,
  type NormalizedError,
} from "@/hooks/useAdminCandidates";

type Filters = AdminCandidateListParams & { q: string };

const parseFiltersFromParams = (params: URLSearchParams): Filters => ({
  status: (params.get("status") as AdminCandidateListParams["status"]) || undefined,
  source: params.get("source") || "",
  q: params.get("q") || "",
  pref: params.get("pref") || "",
  city: params.get("city") || "",
  category: params.get("category") || undefined,
  has_coords:
    params.get("has_coords") === "true"
      ? true
      : params.get("has_coords") === "false"
        ? false
        : undefined,
});

const buildQueryString = (filters: Filters): string => {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.source) params.set("source", filters.source);
  if (filters.q) params.set("q", filters.q);
  if (filters.pref) params.set("pref", filters.pref);
  if (filters.city) params.set("city", filters.city);
  if (filters.category) params.set("category", filters.category);
  if (filters.has_coords !== undefined) params.set("has_coords", String(filters.has_coords));
  return params.toString();
};

const formatDateTime = (value: string | null | undefined) => {
  if (!value) {
    return "-";
  }
  try {
    return new Date(value).toLocaleString("ja-JP");
  } catch (error) {
    return value;
  }
};

function AdminCandidatesPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<Filters>(() => parseFiltersFromParams(searchParams));
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkDryRun, setBulkDryRun] = useState(false);
  const [bulkRejectReason, setBulkRejectReason] = useState("");

  const params = useMemo<AdminCandidateListParams>(
    () => ({
      status: ((): AdminCandidateListParams["status"] => {
        const raw = filters.status?.trim();
        if (!raw) return undefined;
        if (raw === "new" || raw === "reviewing" || raw === "approved" || raw === "rejected") {
          return raw;
        }
        return undefined;
      })(),
      source: filters.source?.trim() || undefined,
      q: filters.q?.trim() || undefined,
      pref: filters.pref?.trim() || undefined,
      city: filters.city?.trim() || undefined,
      category: filters.category || undefined,
      has_coords: filters.has_coords,
      cursor,
    }),
    [filters, cursor],
  );

  const {
    items,
    nextCursor,
    count: totalCount,
    isLoading: loading,
    isInitialLoading,
    error: queryError,
    refetch,
  } = useAdminCandidates({ params });

  const {
    bulkApprove,
    isLoading: approvingBulk,
    error: approveBulkError,
    data: approveBulkData,
  } = useBulkApproveCandidates();
  const {
    bulkReject,
    isLoading: rejectingBulk,
    error: rejectBulkError,
    data: rejectBulkData,
  } = useBulkRejectCandidates();

  const handleSubmit = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setCursor(undefined); // reset pagination
      // Sync filters to URL
      const queryString = buildQueryString(filters);
      router.replace(queryString ? `?${queryString}` : "/admin/candidates", { scroll: false });
      void refetch();
    },
    [filters, refetch, router],
  );

  const handleNext = () => {
    if (!nextCursor) return;
    setCursor(nextCursor);
  };

  const handleRowClick = (candidateId: number) => {
    router.push(`/admin/candidates/${candidateId}`);
  };

  const toggleSelect = useCallback((id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedIds(prev => {
      if (items.length === 0) return prev;
      const allSelected = items.every(i => prev.has(i.id));
      if (allSelected) return new Set();
      return new Set(items.map(i => i.id));
    });
  }, [items]);

  const clearSelection = useCallback(() => setSelectedIds(new Set()), []);

  const performBulkApprove = useCallback(async () => {
    if (selectedIds.size === 0) {
      toast({ title: "候補が選択されていません", variant: "destructive" });
      return;
    }
    try {
      const ids = Array.from(selectedIds);
      const data = await bulkApprove({ ids, dry_run: bulkDryRun });
      toast({
        title: bulkDryRun ? "Dry-run 承認結果" : "バルク承認完了",
        description: `成功: ${data.success_ids.length} / 失敗: ${data.failure_items.length}`,
      });
      if (!bulkDryRun) clearSelection();
    } catch (err) {
      const e = err as NormalizedError;
      toast({ title: "バルク承認失敗", description: e.message, variant: "destructive" });
    }
  }, [bulkApprove, bulkDryRun, clearSelection, selectedIds]);

  const performBulkReject = useCallback(async () => {
    if (selectedIds.size === 0) {
      toast({ title: "候補が選択されていません", variant: "destructive" });
      return;
    }
    const reason = bulkRejectReason.trim();
    if (!reason) {
      toast({ title: "却下理由を入力してください", variant: "destructive" });
      return;
    }
    try {
      const ids = Array.from(selectedIds);
      const data = await bulkReject({ ids, reason, dry_run: bulkDryRun });
      toast({
        title: bulkDryRun ? "Dry-run 却下結果" : "バルク却下完了",
        description: `成功: ${data.success_ids.length} / 失敗: ${data.failure_items.length}`,
      });
      if (!bulkDryRun) clearSelection();
    } catch (err) {
      const e = err as NormalizedError;
      toast({ title: "バルク却下失敗", description: e.message, variant: "destructive" });
    }
  }, [bulkReject, bulkDryRun, bulkRejectReason, clearSelection, selectedIds]);

  const anyBulkLoading = approvingBulk || rejectingBulk;

  const filterControls = useMemo(
    () => (
      <form
        onSubmit={handleSubmit}
        className="mb-6 grid gap-4 rounded-md border border-gray-200 p-4 shadow-sm md:grid-cols-4 lg:grid-cols-7"
      >
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700" htmlFor="status">
            Status
          </label>
          <select
            id="status"
            className="rounded border border-gray-300 px-3 py-2"
            value={filters.status ?? ""}
            onChange={event =>
              setFilters(prev => ({
                ...prev,
                status: event.target.value as AdminCandidateListParams["status"],
              }))
            }
          >
            <option value="">全て</option>
            <option value="new">new</option>
            <option value="reviewing">reviewing</option>
            <option value="approved">approved</option>
            <option value="rejected">rejected</option>
          </select>
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700" htmlFor="source">
            Source
          </label>
          <input
            id="source"
            className="rounded border border-gray-300 px-3 py-2"
            value={filters.source ?? ""}
            onChange={event => setFilters(prev => ({ ...prev, source: event.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700" htmlFor="q">
            キーワード
          </label>
          <input
            id="q"
            className="rounded border border-gray-300 px-3 py-2"
            value={filters.q ?? ""}
            onChange={event => setFilters(prev => ({ ...prev, q: event.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700" htmlFor="pref">
            都道府県スラッグ
          </label>
          <input
            id="pref"
            className="rounded border border-gray-300 px-3 py-2"
            value={filters.pref ?? ""}
            onChange={event => setFilters(prev => ({ ...prev, pref: event.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700" htmlFor="city">
            市区町村スラッグ
          </label>
          <input
            id="city"
            className="rounded border border-gray-300 px-3 py-2"
            value={filters.city ?? ""}
            onChange={event => setFilters(prev => ({ ...prev, city: event.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700" htmlFor="category">
            カテゴリ
          </label>
          <select
            id="category"
            className="rounded border border-gray-300 px-3 py-2"
            value={filters.category ?? ""}
            onChange={event =>
              setFilters(prev => ({
                ...prev,
                category: event.target.value || undefined,
              }))
            }
          >
            <option value="">全て</option>
            <option value="gym">ジム</option>
            <option value="pool">プール</option>
            <option value="court">コート</option>
            <option value="hall">体育館</option>
            <option value="field">グラウンド</option>
            <option value="martial_arts">武道場</option>
            <option value="archery">弓道場</option>
          </select>
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700" htmlFor="has_coords">
            座標
          </label>
          <select
            id="has_coords"
            className="rounded border border-gray-300 px-3 py-2"
            value={filters.has_coords === undefined ? "" : filters.has_coords ? "true" : "false"}
            onChange={event =>
              setFilters(prev => ({
                ...prev,
                has_coords: event.target.value === "" ? undefined : event.target.value === "true",
              }))
            }
          >
            <option value="">全て</option>
            <option value="true">有り</option>
            <option value="false">無し</option>
          </select>
        </div>
        <div className="md:col-span-4 lg:col-span-7 flex flex-wrap gap-4 items-center">
          <button
            type="submit"
            className="rounded bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800"
            disabled={loading}
          >
            {loading ? "検索中..." : "フィルター適用"}
          </button>
          <div className="flex items-center gap-2 text-xs text-gray-600">
            <input
              id="bulk-dry-run"
              type="checkbox"
              checked={bulkDryRun}
              onChange={e => setBulkDryRun(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            <label htmlFor="bulk-dry-run" className="cursor-pointer select-none">
              Dry-run
            </label>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-600">
            <input
              className="rounded border border-gray-300 px-2 py-1"
              placeholder="バルク却下理由"
              value={bulkRejectReason}
              onChange={e => setBulkRejectReason(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={performBulkApprove}
              disabled={anyBulkLoading || selectedIds.size === 0}
              className="rounded bg-green-600 px-3 py-2 text-xs font-semibold text-white hover:bg-green-700 disabled:opacity-50"
            >
              {approvingBulk ? "承認中..." : `バルク承認 (${selectedIds.size})`}
            </button>
            <button
              type="button"
              onClick={performBulkReject}
              disabled={anyBulkLoading || selectedIds.size === 0}
              className="rounded bg-red-600 px-3 py-2 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-50"
            >
              {rejectingBulk ? "却下中..." : `バルク却下 (${selectedIds.size})`}
            </button>
            <button
              type="button"
              onClick={clearSelection}
              disabled={selectedIds.size === 0 || anyBulkLoading}
              className="rounded border border-gray-300 px-3 py-2 text-xs hover:bg-gray-50 disabled:opacity-50"
            >
              選択解除
            </button>
          </div>
        </div>
      </form>
    ),
    [
      bulkDryRun,
      bulkRejectReason,
      clearSelection,
      filters.city,
      filters.pref,
      filters.q,
      filters.source,
      filters.status,
      filters.category,
      filters.has_coords,
      handleSubmit,
      performBulkApprove,
      performBulkReject,
      approvingBulk,
      rejectingBulk,
      selectedIds.size,
      loading,
      anyBulkLoading,
    ],
  );

  useEffect(() => {
    if (queryError) {
      toast({
        title: "候補の取得に失敗しました",
        description: queryError.message,
        variant: "destructive",
      });
    }
  }, [queryError]);

  useEffect(() => {
    if (approveBulkError) {
      toast({
        title: "バルク承認エラー",
        description: approveBulkError.message,
        variant: "destructive",
      });
    }
  }, [approveBulkError]);

  useEffect(() => {
    if (rejectBulkError) {
      toast({
        title: "バルク却下エラー",
        description: rejectBulkError.message,
        variant: "destructive",
      });
    }
  }, [rejectBulkError]);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Gym Candidates</h1>
      {filterControls}
      {loading && isInitialLoading ? (
        <p className="text-sm text-gray-600">読み込み中...</p>
      ) : queryError ? (
        <div className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <p>{queryError.message}</p>
          <button
            type="button"
            className="mt-2 rounded border border-red-400 px-3 py-1 text-xs"
            onClick={() => void refetch()}
          >
            再試行
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2">
                  <input
                    type="checkbox"
                    aria-label="全選択"
                    onChange={toggleSelectAll}
                    checked={items.length > 0 && items.every(i => selectedIds.has(i.id))}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                </th>
                <th className="px-3 py-2 text-left font-semibold text-gray-600">ID</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-600">Status</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-600">カテゴリ</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-600">Name</th>
                <th className="px-3 py-2 text-center font-semibold text-gray-600">Map</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-600">Source</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-600">Fetched</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-600">Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.length === 0 ? (
                <tr>
                  <td className="px-3 py-4 text-center" colSpan={8}>
                    対象の候補がありません。
                  </td>
                </tr>
              ) : (
                items.map(item => (
                  <tr
                    key={item.id}
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => handleRowClick(item.id)}
                  >
                    <td className="px-3 py-2" onClick={e => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        aria-label={`候補 ${item.id} を選択`}
                        checked={selectedIds.has(item.id)}
                        onChange={() => toggleSelect(item.id)}
                        className="h-4 w-4 rounded border-gray-300"
                      />
                    </td>
                    <td className="px-3 py-2">{item.id}</td>
                    <td className="px-3 py-2">{item.status}</td>
                    <td className="px-3 py-2">
                      <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-800">
                        {item.category ?? "-"}
                      </span>
                    </td>
                    <td className="px-3 py-2">{item.name_raw}</td>
                    <td className="px-3 py-2 text-center" onClick={e => e.stopPropagation()}>
                      {item.address_raw ? (
                        <a
                          href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(item.address_raw)}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center justify-center rounded-full bg-blue-100 p-1.5 text-blue-600 hover:bg-blue-200"
                          title={`Google Mapsで開く: ${item.address_raw}`}
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
                            <circle cx="12" cy="10" r="3" />
                          </svg>
                        </a>
                      ) : (
                        <span className="text-gray-300">-</span>
                      )}
                    </td>
                    <td className="px-3 py-2">{item.source?.title ?? "-"}</td>
                    <td className="px-3 py-2">{formatDateTime(item.fetched_at ?? null)}</td>
                    <td className="px-3 py-2">{formatDateTime(item.updated_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500">
          総件数: {totalCount ?? "-"}（表示: {items.length}件）
        </p>
        <button
          type="button"
          className="rounded border border-gray-300 px-4 py-2 text-sm"
          onClick={handleNext}
          disabled={!nextCursor || loading || anyBulkLoading}
        >
          次へ
        </button>
      </div>
    </div>
  );
}

export default function AdminCandidatesPage() {
  return (
    <Suspense fallback={<div className="p-4">読み込み中...</div>}>
      <AdminCandidatesPageContent />
    </Suspense>
  );
}
