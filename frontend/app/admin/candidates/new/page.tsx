"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { toast } from "@/components/ui/use-toast";
import { AdminApiError, createCandidate, approveCandidate } from "@/lib/adminApi";
import type {
  AdminCandidateCreatePayload,
  AdminCandidateItem,
  ApprovePreviewResponse,
  ApproveResponse,
  ApproveResultResponse,
  ApproveSummary,
} from "@/lib/adminApi";

const hasPreview = (response: ApproveResponse): response is ApprovePreviewResponse =>
  "preview" in response;

const hasResult = (response: ApproveResponse): response is ApproveResultResponse =>
  "result" in response;

const parseJsonInput = (input: string): Record<string, unknown> | null => {
  if (!input.trim()) {
    return null;
  }
  const parsed = JSON.parse(input);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("オブジェクト形式のJSONを入力してください");
  }
  return parsed as Record<string, unknown>;
};

const parseOptionalNumber = (value: string, label: string): number | null => {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  if (Number.isNaN(parsed)) {
    throw new Error(`${label}は数値で入力してください`);
  }
  return parsed;
};

type FormState = {
  name_raw: string;
  address_raw: string;
  pref_slug: string;
  city_slug: string;
  latitude: string;
  longitude: string;
  official_url: string;
  parsed_json: string;
};

type FormErrors = Partial<Record<keyof FormState, string>>;

type PreviewState = {
  open: boolean;
  summary: ApproveSummary | null;
  candidate: AdminCandidateItem | null;
  approving: boolean;
  error: string | null;
};

const INITIAL_FORM_STATE: FormState = {
  name_raw: "",
  address_raw: "",
  pref_slug: "",
  city_slug: "",
  latitude: "",
  longitude: "",
  official_url: "",
  parsed_json: "",
};

const INITIAL_PREVIEW_STATE: PreviewState = {
  open: false,
  summary: null,
  candidate: null,
  approving: false,
  error: null,
};

export default function AdminCandidateNewPage() {
  const router = useRouter();
  const [formState, setFormState] = useState<FormState>({ ...INITIAL_FORM_STATE });
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [approveImmediately, setApproveImmediately] = useState(false);
  const [previewState, setPreviewState] = useState<PreviewState>(INITIAL_PREVIEW_STATE);

  const handleFieldChange = useCallback(<K extends keyof FormState>(key: K, value: FormState[K]) => {
    setFormState(prev => ({
      ...prev,
      [key]: value,
    }));
    setFormErrors(prev => ({
      ...prev,
      [key]: undefined,
    }));
  }, []);

  const resetForm = () => {
    setFormState({ ...INITIAL_FORM_STATE });
    setFormErrors({});
  };

  const handlePreviewClose = useCallback(() => {
    const candidate = previewState.candidate;
    setPreviewState(INITIAL_PREVIEW_STATE);
    if (candidate) {
      router.push(`/admin/candidates/${candidate.id}`);
    }
  }, [previewState.candidate, router]);

  const handlePreviewConfirm = useCallback(async () => {
    const candidate = previewState.candidate;
    if (!candidate) {
      return;
    }
    setPreviewState(prev => ({ ...prev, approving: true, error: null }));
    try {
      const response = await approveCandidate(candidate.id, { dry_run: false });
      if (hasResult(response)) {
        const slugLink = `/gyms/${response.result.gym.slug}`;
        toast({
          title: "承認しました",
          description: (
            <a
              className="text-blue-600 underline"
              href={slugLink}
              target="_blank"
              rel="noreferrer"
            >
              {slugLink}
            </a>
          ),
        });
      } else if (hasPreview(response)) {
        toast({ title: "承認結果をプレビューしました" });
      }
      setPreviewState(INITIAL_PREVIEW_STATE);
      router.push(`/admin/candidates/${candidate.id}`);
    } catch (err) {
      if (err instanceof AdminApiError) {
        const detail = typeof err.detail === "string" ? err.detail : err.message;
        toast({
          title: "承認に失敗しました",
          description: detail,
          variant: "destructive",
        });
        setPreviewState(prev => ({ ...prev, error: detail }));
      } else {
        const message = err instanceof Error ? err.message : "承認処理に失敗しました";
        toast({
          title: "承認に失敗しました",
          description: message,
          variant: "destructive",
        });
        setPreviewState(prev => ({ ...prev, error: message }));
      }
    } finally {
      setPreviewState(prev => ({ ...prev, approving: false }));
    }
  }, [previewState.candidate, router]);

  const handleSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setFormErrors({});

      const nextErrors: FormErrors = {};

      if (!formState.name_raw.trim()) {
        nextErrors.name_raw = "名称は必須です";
      }
      if (!formState.pref_slug.trim()) {
        nextErrors.pref_slug = "都道府県スラッグは必須です";
      }
      if (!formState.city_slug.trim()) {
        nextErrors.city_slug = "市区町村スラッグは必須です";
      }

      let latitude: number | null = null;
      let longitude: number | null = null;
      try {
        latitude = parseOptionalNumber(formState.latitude, "緯度");
      } catch (error) {
        nextErrors.latitude = error instanceof Error ? error.message : "緯度が不正です";
      }
      try {
        longitude = parseOptionalNumber(formState.longitude, "経度");
      } catch (error) {
        nextErrors.longitude = error instanceof Error ? error.message : "経度が不正です";
      }

      let parsed: Record<string, unknown> | null = null;
      try {
        parsed = parseJsonInput(formState.parsed_json);
      } catch (error) {
        nextErrors.parsed_json =
          error instanceof Error ? error.message : "JSONの解析に失敗しました";
      }

      if (Object.keys(nextErrors).length > 0) {
        setFormErrors(nextErrors);
        toast({
          title: "入力内容を確認してください",
          variant: "destructive",
        });
        return;
      }

      setSubmitting(true);
      try {
        const payload: AdminCandidateCreatePayload = {
          name_raw: formState.name_raw.trim(),
          address_raw: formState.address_raw.trim() || undefined,
          pref_slug: formState.pref_slug.trim(),
          city_slug: formState.city_slug.trim(),
          latitude: latitude ?? undefined,
          longitude: longitude ?? undefined,
          parsed_json: parsed,
          official_url: formState.official_url.trim() || undefined,
        };
        const created = await createCandidate(payload);
        toast({ title: "候補を作成しました" });
        resetForm();

        if (!approveImmediately) {
          router.push(`/admin/candidates/${created.id}`);
          return;
        }

        try {
          const previewResponse = await approveCandidate(created.id, { dry_run: true });
          if (hasResult(previewResponse)) {
            const slugLink = `/gyms/${previewResponse.result.gym.slug}`;
            toast({
              title: "承認しました",
              description: (
                <a
                  className="text-blue-600 underline"
                  href={slugLink}
                  target="_blank"
                  rel="noreferrer"
                >
                  {slugLink}
                </a>
              ),
            });
            router.push(`/admin/candidates/${created.id}`);
            return;
          }
          if (hasPreview(previewResponse)) {
            toast({ title: "承認結果をプレビューしました" });
            setPreviewState({
              open: true,
              summary: previewResponse.preview,
              candidate: created,
              approving: false,
              error: null,
            });
          }
        } catch (err) {
          if (err instanceof AdminApiError) {
            const detail = typeof err.detail === "string" ? err.detail : err.message;
            toast({
              title: "承認プレビューに失敗しました",
              description: detail,
              variant: "destructive",
            });
          } else {
            toast({
              title: "承認プレビューに失敗しました",
              description: err instanceof Error ? err.message : "不明なエラーです",
              variant: "destructive",
            });
          }
          router.push(`/admin/candidates/${created.id}`);
        }
      } catch (err) {
        if (err instanceof AdminApiError) {
          const detail = typeof err.detail === "string" ? err.detail : err.message;
          toast({
            title: "候補の作成に失敗しました",
            description: detail,
            variant: "destructive",
          });
        } else {
          toast({
            title: "候補の作成に失敗しました",
            description: err instanceof Error ? err.message : "不明なエラーです",
            variant: "destructive",
          });
        }
      } finally {
        setSubmitting(false);
      }
    },
    [approveImmediately, formState, router],
  );

  const renderPreview = useMemo(() => {
    if (!previewState.open || !previewState.summary) {
      return null;
    }
    const { gym, equipments } = previewState.summary;
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
        <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-md bg-white p-6 shadow-lg">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">承認結果プレビュー</h2>
            <button
              type="button"
              className="text-sm text-gray-500"
              onClick={handlePreviewClose}
              disabled={previewState.approving}
            >
              閉じる
            </button>
          </div>
          <section className="mb-4 space-y-2 text-sm">
            <h3 className="text-sm font-semibold text-gray-700">ジム情報</h3>
            <div className="rounded border border-gray-200 p-3">
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
                <span className="font-medium">位置:</span> {gym.pref_slug ?? "-"} / {gym.city_slug ?? "-"} (
                {gym.latitude ?? "-"}, {gym.longitude ?? "-"})
              </p>
            </div>
          </section>
          <section className="space-y-2 text-sm">
            <h3 className="text-sm font-semibold text-gray-700">設備サマリ</h3>
            <div className="rounded border border-gray-200 p-3">
              <p>
                追加: {equipments.inserted} / 更新: {equipments.updated} / 合計: {equipments.total}
              </p>
            </div>
          </section>
          {previewState.error ? (
            <p className="mt-4 text-sm text-red-600">{previewState.error}</p>
          ) : null}
          <div className="mt-6 flex justify-end gap-3">
            <button
              type="button"
              className="rounded border border-gray-300 px-4 py-2 text-sm"
              onClick={handlePreviewClose}
              disabled={previewState.approving}
            >
              詳細ページへ移動
            </button>
            <button
              type="button"
              className="rounded bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-blue-300"
              onClick={handlePreviewConfirm}
              disabled={previewState.approving}
            >
              {previewState.approving ? "承認処理中..." : "承認を確定"}
            </button>
          </div>
        </div>
      </div>
    );
  }, [handlePreviewClose, handlePreviewConfirm, previewState]);

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">候補の手動入稿</h1>
        <p className="mt-2 text-sm text-gray-600">
          必須項目を入力して候補を作成してください。作成後は詳細ページに遷移します。
        </p>
      </div>
      <form className="grid gap-4 rounded-md border border-gray-200 bg-white p-6 shadow-sm" onSubmit={handleSubmit}>
        <div className="grid gap-2">
          <label className="text-sm font-medium text-gray-700" htmlFor="name_raw">
            名称 (必須)
          </label>
          <input
            id="name_raw"
            className="rounded border border-gray-300 px-3 py-2"
            value={formState.name_raw}
            onChange={event => handleFieldChange("name_raw", event.target.value)}
            disabled={submitting}
            required
          />
          {formErrors.name_raw ? (
            <p className="text-sm text-red-600">{formErrors.name_raw}</p>
          ) : null}
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-medium text-gray-700" htmlFor="address_raw">
            住所
          </label>
          <input
            id="address_raw"
            className="rounded border border-gray-300 px-3 py-2"
            value={formState.address_raw}
            onChange={event => handleFieldChange("address_raw", event.target.value)}
            disabled={submitting}
          />
          {formErrors.address_raw ? (
            <p className="text-sm text-red-600">{formErrors.address_raw}</p>
          ) : null}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-700" htmlFor="pref_slug">
              都道府県スラッグ (必須)
            </label>
            <input
              id="pref_slug"
              className="rounded border border-gray-300 px-3 py-2"
              value={formState.pref_slug}
              onChange={event => handleFieldChange("pref_slug", event.target.value)}
              disabled={submitting}
              required
            />
            {formErrors.pref_slug ? (
              <p className="text-sm text-red-600">{formErrors.pref_slug}</p>
            ) : null}
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-700" htmlFor="city_slug">
              市区町村スラッグ (必須)
            </label>
            <input
              id="city_slug"
              className="rounded border border-gray-300 px-3 py-2"
              value={formState.city_slug}
              onChange={event => handleFieldChange("city_slug", event.target.value)}
              disabled={submitting}
              required
            />
            {formErrors.city_slug ? (
              <p className="text-sm text-red-600">{formErrors.city_slug}</p>
            ) : null}
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-700" htmlFor="latitude">
              緯度
            </label>
            <input
              id="latitude"
              className="rounded border border-gray-300 px-3 py-2"
              value={formState.latitude}
              onChange={event => handleFieldChange("latitude", event.target.value)}
              disabled={submitting}
            />
            {formErrors.latitude ? (
              <p className="text-sm text-red-600">{formErrors.latitude}</p>
            ) : null}
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-700" htmlFor="longitude">
              経度
            </label>
            <input
              id="longitude"
              className="rounded border border-gray-300 px-3 py-2"
              value={formState.longitude}
              onChange={event => handleFieldChange("longitude", event.target.value)}
              disabled={submitting}
            />
            {formErrors.longitude ? (
              <p className="text-sm text-red-600">{formErrors.longitude}</p>
            ) : null}
          </div>
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-medium text-gray-700" htmlFor="official_url">
            公式サイトURL
          </label>
          <input
            id="official_url"
            className="rounded border border-gray-300 px-3 py-2"
            value={formState.official_url}
            onChange={event => handleFieldChange("official_url", event.target.value)}
            disabled={submitting}
          />
          {formErrors.official_url ? (
            <p className="text-sm text-red-600">{formErrors.official_url}</p>
          ) : null}
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-medium text-gray-700" htmlFor="parsed_json">
            追加JSON
          </label>
          <textarea
            id="parsed_json"
            className="h-48 rounded border border-gray-300 px-3 py-2 font-mono text-sm"
            value={formState.parsed_json}
            onChange={event => handleFieldChange("parsed_json", event.target.value)}
            disabled={submitting}
          />
          {formErrors.parsed_json ? (
            <p className="text-sm text-red-600">{formErrors.parsed_json}</p>
          ) : null}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="h-4 w-4"
            checked={approveImmediately}
            onChange={event => setApproveImmediately(event.target.checked)}
            disabled={submitting}
          />
          作成後にすぐ承認する
        </label>
        <div className="flex justify-end gap-3">
          <button
            type="submit"
            className="rounded bg-blue-600 px-4 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:bg-blue-300"
            disabled={submitting}
          >
            {submitting ? "送信中..." : "候補を作成"}
          </button>
        </div>
      </form>
      {renderPreview}
    </div>
  );
}
