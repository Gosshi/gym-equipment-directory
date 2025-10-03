"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import type { AdminCandidateItem, AdminCandidateListParams } from "@/lib/adminApi";
import { AdminApiError, listCandidates } from "@/lib/adminApi";
import { toast } from "@/components/ui/use-toast";

type Filters = AdminCandidateListParams & { q: string };

const DEFAULT_FILTERS: Filters = {
  status: "",
  source: "",
  q: "",
  pref: "",
  city: "",
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

export default function AdminCandidatesPage() {
  const router = useRouter();
  const [filters, setFilters] = useState<Filters>({ ...DEFAULT_FILTERS });
  const [items, setItems] = useState<AdminCandidateItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const buildParams = useCallback(
    (cursor?: string | null): AdminCandidateListParams => {
      const rawStatus = filters.status?.trim();
      const statusValue = rawStatus
        ? (rawStatus as Exclude<AdminCandidateListParams["status"], "" | null | undefined>)
        : undefined;

      return {
        status: statusValue,
        source: filters.source?.trim() || undefined,
        q: filters.q?.trim() || undefined,
        pref: filters.pref?.trim() || undefined,
        city: filters.city?.trim() || undefined,
        cursor: cursor || undefined,
      };
    },
    [filters],
  );

  const fetchCandidates = useCallback(
    async (cursor?: string | null) => {
      setLoading(true);
      setError(null);
      try {
        const response = await listCandidates(buildParams(cursor));
        setItems(response.items);
        setNextCursor(response.next_cursor ?? null);
        setTotalCount(typeof response.count === "number" ? response.count : response.items.length);
      } catch (err) {
        if (err instanceof AdminApiError) {
          setError(err.message);
        } else {
          setError("ネットワークエラーが発生しました");
        }
        setTotalCount(null);
      } finally {
        setLoading(false);
      }
    },
    [buildParams],
  );

  useEffect(() => {
    void fetchCandidates();
  }, [fetchCandidates]);

  const handleSubmit = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      void fetchCandidates();
    },
    [fetchCandidates],
  );

  const handleNext = () => {
    if (!nextCursor) {
      return;
    }
    void fetchCandidates(nextCursor);
  };

  const handleRowClick = (candidateId: number) => {
    router.push(`/admin/candidates/${candidateId}`);
  };

  const filterControls = useMemo(
    () => (
      <form
        onSubmit={handleSubmit}
        className="mb-6 grid gap-4 rounded-md border border-gray-200 p-4 shadow-sm md:grid-cols-5"
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
        <div className="md:col-span-5">
          <button
            type="submit"
            className="rounded bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800"
            disabled={loading}
          >
            {loading ? "検索中..." : "フィルター適用"}
          </button>
        </div>
      </form>
    ),
    [filters.city, filters.pref, filters.q, filters.source, filters.status, loading, handleSubmit],
  );

  useEffect(() => {
    if (error) {
      toast({
        title: "候補の取得に失敗しました",
        description: error,
        variant: "destructive",
      });
    }
  }, [error]);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Gym Candidates</h1>
      {filterControls}
      {loading ? (
        <p className="text-sm text-gray-600">読み込み中...</p>
      ) : error ? (
        <div className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <p>{error}</p>
          <button
            type="button"
            className="mt-2 rounded border border-red-400 px-3 py-1 text-xs"
            onClick={() => fetchCandidates()}
          >
            再試行
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-semibold text-gray-600">ID</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-600">Status</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-600">Name</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-600">Source</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-600">Fetched</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-600">Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.length === 0 ? (
                <tr>
                  <td className="px-3 py-4 text-center" colSpan={6}>
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
                    <td className="px-3 py-2">{item.id}</td>
                    <td className="px-3 py-2">{item.status}</td>
                    <td className="px-3 py-2">{item.name_raw}</td>
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
          disabled={!nextCursor || loading}
        >
          次へ
        </button>
      </div>
    </div>
  );
}
