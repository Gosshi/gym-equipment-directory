"use client";

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { toast } from "@/components/ui/use-toast";
import {
  AdminApiError,
  AdminCandidateDetail,
  AdminCandidateItem,
  ApprovePreviewResponse,
  ApproveResultResponse,
  ApproveSummary,
  ApproveOverride,
  getCandidate,
  approveCandidate,
  patchCandidate,
  rejectCandidate,
} from "@/lib/adminApi";

const formatDateTime = (value: string | undefined | null) => {
  if (!value) {
    return "-";
  }
  try {
    return new Date(value).toLocaleString("ja-JP");
  } catch (error) {
    return value;
  }
};

type FormState = {
  name_raw: string;
  address_raw: string;
  pref_slug: string;
  city_slug: string;
  latitude: string;
  longitude: string;
  parsed_json: string;
};

const toFormState = (candidate: AdminCandidateDetail): FormState => ({
  name_raw: candidate.name_raw ?? "",
  address_raw: candidate.address_raw ?? "",
  pref_slug: candidate.pref_slug ?? "",
  city_slug: candidate.city_slug ?? "",
  latitude:
    candidate.latitude !== undefined && candidate.latitude !== null
      ? String(candidate.latitude)
      : "",
  longitude:
    candidate.longitude !== undefined && candidate.longitude !== null
      ? String(candidate.longitude)
      : "",
  parsed_json: candidate.parsed_json ? JSON.stringify(candidate.parsed_json, null, 2) : "",
});

const parseJsonInput = (input: string): Record<string, unknown> | null => {
  if (!input.trim()) {
    return null;
  }
  return JSON.parse(input);
};

type PreviewState = {
  summary: ApproveSummary | null;
  open: boolean;
};

const INITIAL_PREVIEW_STATE: PreviewState = {
  summary: null,
  open: false,
};

type CandidateActionState = "idle" | "saving" | "approving" | "rejecting";

export default function AdminCandidateDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const candidateId = Number(params?.id);
  const [candidate, setCandidate] = useState<AdminCandidateDetail | null>(null);
  const [formState, setFormState] = useState<FormState | null>(null);
  const [preview, setPreview] = useState<PreviewState>(INITIAL_PREVIEW_STATE);
  const [actionState, setActionState] = useState<CandidateActionState>("idle");
  const [rejectReason, setRejectReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadCandidate = useCallback(async () => {
    if (Number.isNaN(candidateId)) {
      setError("候補IDが不正です");
      return;
    }
    try {
      const detail = await getCandidate(candidateId);
      setCandidate(detail);
      setFormState(toFormState(detail));
      setError(null);
    } catch (err) {
      if (err instanceof AdminApiError) {
        setError(err.message);
      } else {
        setError("候補の取得に失敗しました");
      }
    }
  }, [candidateId]);

  useEffect(() => {
    void loadCandidate();
  }, [loadCandidate]);

  const updateCandidateState = (item: AdminCandidateItem) => {
    setCandidate(prev => {
      if (!prev) {
        return null;
      }
      const merged: AdminCandidateDetail = {
        ...prev,
        ...item,
      };
      setFormState(toFormState(merged));
      return merged;
    });
  };

  const handleInputChange = <T extends keyof FormState>(key: T, value: FormState[T]) => {
    setFormState(prev => (prev ? { ...prev, [key]: value } : prev));
  };

  const handleSave = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState || !candidate) {
      return;
    }
    let parsed: Record<string, unknown> | null = null;
    try {
      parsed = parseJsonInput(formState.parsed_json);
    } catch (err) {
      toast({
        title: "JSONの解析に失敗しました",
        description: err instanceof Error ? err.message : "不正なJSONです",
        variant: "destructive",
      });
      return;
    }
    setActionState("saving");
    try {
      const payload = {
        name_raw: formState.name_raw || candidate.name_raw,
        address_raw: formState.address_raw || null,
        pref_slug: formState.pref_slug || null,
        city_slug: formState.city_slug || null,
        latitude: formState.latitude ? Number(formState.latitude) : null,
        longitude: formState.longitude ? Number(formState.longitude) : null,
        parsed_json: parsed,
      };
      const updated = await patchCandidate(candidate.id, payload);
      updateCandidateState(updated);
      toast({ title: "候補を保存しました" });
    } catch (err) {
      if (err instanceof AdminApiError && err.status === 400) {
        const detail = typeof err.detail === "string" ? err.detail : err.message;
        toast({
          title: "保存に失敗しました",
          description: detail,
          variant: "destructive",
        });
      } else {
        toast({
          title: "保存に失敗しました",
          description: err instanceof Error ? err.message : "不明なエラーです",
          variant: "destructive",
        });
      }
    } finally {
      setActionState("idle");
    }
  };

  const handleDryRun = async () => {
    if (!candidate) {
      return;
    }
    setActionState("approving");
    try {
      const response = (await approveCandidate(candidate.id, {
        dry_run: true,
      })) as ApprovePreviewResponse;
      setPreview({ summary: response.preview, open: true });
    } catch (err) {
      if (err instanceof AdminApiError) {
        toast({
          title: "Dry-run に失敗しました",
          description: typeof err.detail === "string" ? err.detail : err.message,
          variant: "destructive",
        });
      } else {
        toast({
          title: "Dry-run に失敗しました",
          description: err instanceof Error ? err.message : "不明なエラーです",
          variant: "destructive",
        });
      }
    } finally {
      setActionState("idle");
    }
  };

  const performApproval = async (override?: ApproveOverride | null) => {
    if (!candidate) {
      return;
    }
    setActionState("approving");
    try {
      const response = (await approveCandidate(candidate.id, {
        dry_run: false,
        override: override ?? undefined,
      })) as ApproveResultResponse;
      const { result } = response;
      const slugLink = `/gyms/${result.gym.slug}`;
      toast({
        title: "承認しました",
        description: (
          <a className="text-blue-600 underline" href={slugLink} target="_blank" rel="noreferrer">
            {slugLink}
          </a>
        ),
      });
      setPreview({ summary: result, open: true });
      void loadCandidate();
    } catch (err) {
      if (err instanceof AdminApiError) {
        if (err.status === 409) {
          const overrideName = window.prompt(
            "slug が重複しています。上書きする名称を入力してください",
          );
          if (overrideName) {
            await performApproval({ name: overrideName });
          }
          return;
        }
        toast({
          title: "承認に失敗しました",
          description: typeof err.detail === "string" ? err.detail : err.message,
          variant: "destructive",
        });
      } else {
        toast({
          title: "承認に失敗しました",
          description: err instanceof Error ? err.message : "不明なエラーです",
          variant: "destructive",
        });
      }
    } finally {
      setActionState("idle");
    }
  };

  const handleReject = async () => {
    if (!candidate || !rejectReason.trim()) {
      toast({
        title: "却下理由を入力してください",
        variant: "destructive",
      });
      return;
    }
    if (!window.confirm("この候補を却下しますか？")) {
      return;
    }
    setActionState("rejecting");
    try {
      const updated = await rejectCandidate(candidate.id, { reason: rejectReason.trim() });
      updateCandidateState(updated);
      toast({ title: "候補を却下しました" });
    } catch (err) {
      if (err instanceof AdminApiError) {
        toast({
          title: "却下に失敗しました",
          description: typeof err.detail === "string" ? err.detail : err.message,
          variant: "destructive",
        });
      } else {
        toast({
          title: "却下に失敗しました",
          description: err instanceof Error ? err.message : "不明なエラーです",
          variant: "destructive",
        });
      }
    } finally {
      setActionState("idle");
    }
  };

  const closePreview = useCallback(() => {
    setPreview({ summary: null, open: false });
  }, []);

  const isLoading = !candidate && !error;

  const renderPreview = useMemo(() => {
    if (!preview.open || !preview.summary) {
      return null;
    }
    const { gym, equipments } = preview.summary;
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
        <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-md bg-white p-6 shadow-lg">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">承認結果プレビュー</h2>
            <button type="button" className="text-sm text-gray-500" onClick={closePreview}>
              閉じる
            </button>
          </div>
          <section className="mb-4 space-y-2">
            <h3 className="text-sm font-semibold text-gray-700">ジム情報</h3>
            <div className="rounded border border-gray-200 p-3 text-sm">
              <p>
                <span className="font-medium">名称:</span> {gym.name}
              </p>
              <p>
                <span className="font-medium">Slug:</span> <code>{gym.slug}</code>
              </p>
              <p>
                <span className="font-medium">Canonical ID:</span> {gym.canonical_id}
              </p>
              <p>
                <span className="font-medium">住所:</span> {gym.address ?? "-"}
              </p>
              <p>
                <span className="font-medium">位置:</span> {gym.pref_slug ?? "-"} /{" "}
                {gym.city_slug ?? "-"} ({gym.latitude ?? "-"}, {gym.longitude ?? "-"})
              </p>
            </div>
          </section>
          <section className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-700">設備サマリ</h3>
            <div className="rounded border border-gray-200 p-3 text-sm">
              <p>
                追加: {equipments.inserted} / 更新: {equipments.updated} / 合計: {equipments.total}
              </p>
            </div>
          </section>
        </div>
      </div>
    );
  }, [preview, closePreview]);

  if (error) {
    return (
      <div className="rounded border border-red-200 bg-red-50 p-6">
        <p className="text-sm text-red-700">{error}</p>
        <button
          type="button"
          className="mt-3 rounded border border-red-400 px-3 py-1 text-xs"
          onClick={() => void loadCandidate()}
        >
          再読み込み
        </button>
      </div>
    );
  }

  if (isLoading || !candidate || !formState) {
    return <p className="text-sm text-gray-600">読み込み中...</p>;
  }

  return (
    <Fragment>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">候補詳細 #{candidate.id}</h1>
          <p className="text-sm text-gray-500">
            ステータス: <span className="font-medium text-gray-700">{candidate.status}</span>
          </p>
        </div>
        <button type="button" className="text-sm text-gray-500" onClick={() => router.back()}>
          一覧へ戻る
        </button>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <form
          onSubmit={handleSave}
          className="flex flex-col gap-4 rounded border border-gray-200 p-4 shadow-sm"
        >
          <h2 className="text-lg font-semibold">編集</h2>
          <label className="flex flex-col gap-2 text-sm">
            <span className="font-medium">名称</span>
            <input
              className="rounded border border-gray-300 px-3 py-2"
              value={formState.name_raw}
              onChange={event => handleInputChange("name_raw", event.target.value)}
            />
          </label>
          <label className="flex flex-col gap-2 text-sm">
            <span className="font-medium">住所</span>
            <textarea
              className="h-20 rounded border border-gray-300 px-3 py-2"
              value={formState.address_raw}
              onChange={event => handleInputChange("address_raw", event.target.value)}
            />
          </label>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-2 text-sm">
              <span className="font-medium">都道府県スラッグ</span>
              <input
                className="rounded border border-gray-300 px-3 py-2"
                value={formState.pref_slug}
                onChange={event => handleInputChange("pref_slug", event.target.value)}
              />
            </label>
            <label className="flex flex-col gap-2 text-sm">
              <span className="font-medium">市区町村スラッグ</span>
              <input
                className="rounded border border-gray-300 px-3 py-2"
                value={formState.city_slug}
                onChange={event => handleInputChange("city_slug", event.target.value)}
              />
            </label>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-2 text-sm">
              <span className="font-medium">緯度</span>
              <input
                className="rounded border border-gray-300 px-3 py-2"
                value={formState.latitude}
                onChange={event => handleInputChange("latitude", event.target.value)}
              />
            </label>
            <label className="flex flex-col gap-2 text-sm">
              <span className="font-medium">経度</span>
              <input
                className="rounded border border-gray-300 px-3 py-2"
                value={formState.longitude}
                onChange={event => handleInputChange("longitude", event.target.value)}
              />
            </label>
          </div>
          <label className="flex flex-col gap-2 text-sm">
            <span className="font-medium">解析済みJSON</span>
            <textarea
              className="h-52 rounded border border-gray-300 px-3 py-2 font-mono text-xs"
              value={formState.parsed_json}
              onChange={event => handleInputChange("parsed_json", event.target.value)}
            />
          </label>
          <button
            type="submit"
            className="mt-2 rounded bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800"
            disabled={actionState === "saving"}
          >
            {actionState === "saving" ? "保存中..." : "保存"}
          </button>
        </form>
        <div className="flex flex-col gap-4">
          <section className="rounded border border-gray-200 p-4 shadow-sm">
            <h2 className="text-lg font-semibold">スクレイプ情報</h2>
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="font-medium">URL</dt>
                <dd>
                  <a
                    className="text-blue-600 underline"
                    href={candidate.scraped_page.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {candidate.scraped_page.url}
                  </a>
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">Fetched</dt>
                <dd>{formatDateTime(candidate.scraped_page.fetched_at)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">HTTP Status</dt>
                <dd>{candidate.scraped_page.http_status ?? "-"}</dd>
              </div>
            </dl>
          </section>
          <section className="rounded border border-gray-200 p-4 shadow-sm">
            <h2 className="text-lg font-semibold">類似ジム</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {(candidate.similar ?? []).length === 0 ? (
                <li className="text-gray-500">類似ジムはありません</li>
              ) : (
                candidate.similar?.map(similar => (
                  <li key={similar.gym_id}>
                    <a
                      className="text-blue-600 underline"
                      href={`/gyms/${similar.gym_slug}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {similar.gym_name} ({similar.gym_slug})
                    </a>
                  </li>
                ))
              )}
            </ul>
          </section>
          <section className="rounded border border-gray-200 p-4 shadow-sm">
            <h2 className="text-lg font-semibold">メタ情報</h2>
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="font-medium">Fetched</dt>
                <dd>{formatDateTime(candidate.fetched_at)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">Updated</dt>
                <dd>{formatDateTime(candidate.updated_at)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">Source</dt>
                <dd>{candidate.source?.title ?? "-"}</dd>
              </div>
            </dl>
          </section>
        </div>
      </div>
      <section className="mt-6 rounded border border-gray-200 p-4 shadow-sm">
        <h2 className="text-lg font-semibold">アクション</h2>
        <div className="mt-3 flex flex-wrap gap-3">
          <button
            type="button"
            className="rounded border border-gray-300 px-4 py-2 text-sm"
            onClick={handleDryRun}
            disabled={actionState !== "idle"}
          >
            {actionState === "approving" ? "処理中..." : "Dry-run 承認"}
          </button>
          <button
            type="button"
            className="rounded bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700"
            onClick={() => void performApproval()}
            disabled={actionState !== "idle"}
          >
            本承認
          </button>
          <div className="flex items-center gap-2">
            <textarea
              className="h-16 w-64 rounded border border-gray-300 px-3 py-2 text-sm"
              placeholder="却下理由"
              value={rejectReason}
              onChange={event => setRejectReason(event.target.value)}
            />
            <button
              type="button"
              className="rounded bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
              onClick={handleReject}
              disabled={actionState !== "idle"}
            >
              却下
            </button>
          </div>
        </div>
      </section>
      {renderPreview}
    </Fragment>
  );
}
