"use client";

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { toast } from "@/components/ui/use-toast";
import {
  AdminApiError,
  AdminCandidateDetail,
  AdminCandidateItem,
  ApprovePreviewResponse,
  ApproveResponse,
  ApproveResultResponse,
  ApproveSummary,
  ApproveOverride,
  getCandidate,
  approveCandidate,
  patchCandidate,
  rejectCandidate,
  geocodeCandidate,
  scrapeCandidateOfficialUrl,
} from "@/lib/adminApi";

import GymMap from "@/components/gym/GymMap";

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
  official_url: string;
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
  official_url: candidate.official_url ?? "",
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

type OverrideFormValues = {
  name: string;
  pref_slug: string;
  city_slug: string;
  address: string;
  latitude: string;
  longitude: string;
  official_url: string;
};

const DEFAULT_OVERRIDE_VALUES: OverrideFormValues = {
  name: "",
  pref_slug: "",
  city_slug: "",
  address: "",
  latitude: "",
  longitude: "",
  official_url: "",
};

const toOverrideFormValues = (override?: ApproveOverride | null): Partial<OverrideFormValues> => {
  if (!override) {
    return {};
  }
  return {
    name: override.name ?? "",
    pref_slug: override.pref_slug ?? "",
    city_slug: override.city_slug ?? "",
    address: override.address ?? "",
    latitude:
      override.latitude !== undefined && override.latitude !== null
        ? String(override.latitude)
        : "",
    longitude:
      override.longitude !== undefined && override.longitude !== null
        ? String(override.longitude)
        : "",
    official_url: override.official_url ?? "",
  };
};

type OverrideDialogMode = "missingFields" | "conflict";

type OverrideDialogState = {
  open: boolean;
  mode: OverrideDialogMode;
  message: string | null;
  error: string | null;
  values: OverrideFormValues;
  baseOverride: ApproveOverride | null;
};

const INITIAL_OVERRIDE_DIALOG: OverrideDialogState = {
  open: false,
  mode: "missingFields",
  message: null,
  error: null,
  values: { ...DEFAULT_OVERRIDE_VALUES },
  baseOverride: null,
};

type ScrapePreviewState = {
  open: boolean;
  data: Record<string, unknown> | null;
};

const INITIAL_SCRAPE_PREVIEW: ScrapePreviewState = {
  open: false,
  data: null,
};

const hasPreview = (response: ApproveResponse): response is ApprovePreviewResponse =>
  "preview" in response;

const hasResult = (response: ApproveResponse): response is ApproveResultResponse =>
  "result" in response;

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

const isJsonObject = (value: JsonValue): value is { [key: string]: JsonValue } =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const isJsonPrimitive = (value: JsonValue): value is string | number | boolean | null =>
  typeof value === "string" ||
  typeof value === "number" ||
  typeof value === "boolean" ||
  value === null;

const updateJsonAtPath = (
  value: JsonValue,
  path: Array<string | number>,
  nextValue: JsonValue,
): JsonValue => {
  if (path.length === 0) {
    return nextValue;
  }
  const [head, ...rest] = path;
  if (Array.isArray(value)) {
    const next = [...value];
    const index = Number(head);
    next[index] = updateJsonAtPath(next[index] ?? null, rest, nextValue);
    return next;
  }
  if (isJsonObject(value)) {
    const next = { ...value };
    next[String(head)] = updateJsonAtPath(next[String(head)] ?? null, rest, nextValue);
    return next;
  }
  const fallback: JsonValue = typeof head === "number" ? [] : {};
  return updateJsonAtPath(fallback, path, nextValue);
};

const parseCommaSeparated = (input: string) =>
  input
    .split(",")
    .map(part => part.trim())
    .filter(Boolean);

export default function AdminCandidateDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const candidateId = Number(params?.id);
  const [candidate, setCandidate] = useState<AdminCandidateDetail | null>(null);
  const [formState, setFormState] = useState<FormState | null>(null);
  const [preview, setPreview] = useState<PreviewState>(INITIAL_PREVIEW_STATE);
  const [scrapePreview, setScrapePreview] = useState<ScrapePreviewState>(INITIAL_SCRAPE_PREVIEW);
  const [actionState, setActionState] = useState<CandidateActionState>("idle");
  const [rejectReason, setRejectReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [overrideDialog, setOverrideDialog] =
    useState<OverrideDialogState>(INITIAL_OVERRIDE_DIALOG);
  const [isScraping, setIsScraping] = useState(false);
  const [isParsedJsonExpanded, setIsParsedJsonExpanded] = useState(false);
  const [isRawJsonVisible, setIsRawJsonVisible] = useState(false);

  const parsedJsonError = useMemo(() => {
    if (!formState?.parsed_json.trim()) {
      return null;
    }
    try {
      JSON.parse(formState.parsed_json);
      return null;
    } catch (jsonError) {
      return jsonError instanceof Error ? jsonError.message : "JSONの解析に失敗しました";
    }
  }, [formState?.parsed_json]);

  const parsedJsonValue = useMemo<JsonValue>(() => {
    if (!formState?.parsed_json.trim()) {
      return {};
    }
    try {
      return JSON.parse(formState.parsed_json) as JsonValue;
    } catch {
      return {};
    }
  }, [formState?.parsed_json]);

  const isParsedJsonEmpty = useMemo(
    () => isJsonObject(parsedJsonValue) && Object.keys(parsedJsonValue).length === 0,
    [parsedJsonValue],
  );

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
        official_url: formState.official_url || null,
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
      const response = await approveCandidate(candidate.id, {
        dry_run: true,
      });
      if (hasPreview(response)) {
        setPreview({ summary: response.preview, open: true });
      } else if (hasResult(response)) {
        setPreview({ summary: response.result, open: true });
      }
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

  const openOverrideDialog = useCallback(
    (
      mode: OverrideDialogMode,
      message: string | null = null,
      options?: { values?: Partial<OverrideFormValues>; baseOverride?: ApproveOverride | null },
    ) => {
      if (!formState || !candidate) {
        return;
      }

      const defaultValues: OverrideFormValues = {
        name: formState.name_raw || candidate.name_raw || "",
        pref_slug: formState.pref_slug ?? "",
        city_slug: formState.city_slug ?? "",
        address: formState.address_raw ?? "",
        latitude: formState.latitude ?? "",
        longitude: formState.longitude ?? "",
        official_url: formState.official_url ?? "",
      };

      const mergedValues: OverrideFormValues = {
        ...defaultValues,
        ...toOverrideFormValues(options?.baseOverride ?? null),
        ...(options?.values ?? {}),
      };

      setOverrideDialog({
        open: true,
        mode,
        message,
        error: null,
        values: mergedValues,
        baseOverride: options?.baseOverride ?? null,
      });
    },
    [candidate, formState],
  );

  const closeOverrideDialog = useCallback(() => {
    setOverrideDialog(INITIAL_OVERRIDE_DIALOG);
  }, []);

  const performApproval = useCallback(
    async (override?: ApproveOverride | null): Promise<boolean> => {
      if (!candidate) {
        return false;
      }
      setActionState("approving");
      try {
        const response = await approveCandidate(candidate.id, {
          dry_run: false,
          override: override ?? undefined,
        });
        if (hasResult(response)) {
          const { result } = response;
          const slugLink = `/gyms/${result.gym.slug}`;
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
          setPreview({ summary: result, open: true });
          void loadCandidate();
          return true;
        }
        if (hasPreview(response)) {
          setPreview({ summary: response.preview, open: true });
          toast({ title: "承認結果をプレビューしました" });
        }
        return true;
      } catch (err) {
        if (err instanceof AdminApiError) {
          if (err.status === 400) {
            const detailMessage =
              typeof err.detail === "string"
                ? err.detail
                : err instanceof Error
                  ? err.message
                  : "承認に必要な情報が不足しています";
            openOverrideDialog("missingFields", detailMessage, {
              baseOverride: override ?? null,
            });
            return false;
          }
          if (err.status === 409) {
            const detailMessage =
              typeof err.detail === "string"
                ? err.detail
                : err instanceof Error
                  ? err.message
                  : "slug が重複しています";
            openOverrideDialog("conflict", detailMessage, {
              baseOverride: override ?? null,
            });
            return false;
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
        return false;
      } finally {
        setActionState("idle");
      }
    },
    [candidate, loadCandidate, openOverrideDialog],
  );

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
      const updated = await rejectCandidate(candidate.id, rejectReason.trim());
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

  const closeScrapePreview = useCallback(() => {
    setScrapePreview(INITIAL_SCRAPE_PREVIEW);
  }, []);

  const handleScrapeApply = useCallback(() => {
    if (!scrapePreview.data) return;
    setFormState(prev => {
      if (!prev) return null;
      return {
        ...prev,
        parsed_json: JSON.stringify(scrapePreview.data, null, 2),
      };
    });
    closeScrapePreview();
    toast({
      title: "反映しました",
      description: "必ず「保存」ボタンを押して変更を確定してください",
    });
  }, [scrapePreview.data, closeScrapePreview]);

  const updateParsedJsonValue = useCallback(
    (path: Array<string | number>, nextValue: JsonValue) => {
      setFormState(prev => {
        if (!prev) {
          return prev;
        }
        let base: JsonValue = {};
        if (prev.parsed_json.trim()) {
          try {
            base = JSON.parse(prev.parsed_json) as JsonValue;
          } catch {
            return prev;
          }
        }
        const updated = updateJsonAtPath(base, path, nextValue);
        return {
          ...prev,
          parsed_json: JSON.stringify(updated, null, 2),
        };
      });
    },
    [],
  );

  // デフォルトで展開すべき重要キー
  const EXPANDED_BY_DEFAULT_KEYS = new Set([
    "name",
    "address",
    "tel",
    "phone",
    "email",
    "access",
    "category",
    "categories",
    "url",
    "official_url",
    "description",
  ]);

  // デフォルトで閉じるべき長いキー
  const COLLAPSED_BY_DEFAULT_KEYS = new Set([
    "equipments_structured",
    "equipments",
    "opening_hours",
    "hours",
    "fees",
    "fee_structure",
    "schedule",
    "pricing",
    "amenities",
    "facilities",
  ]);

  const getSummaryPreview = (entry: JsonValue, key: string): string => {
    if (Array.isArray(entry)) {
      const count = entry.length;
      if (count === 0) return "空の配列";
      const primitivesOnly = entry.every(isJsonPrimitive);
      if (primitivesOnly && count <= 3) {
        return entry.map(item => (item === null ? "null" : String(item))).join(", ");
      }
      return `${count}件`;
    }
    if (isJsonObject(entry)) {
      const keys = Object.keys(entry);
      if (keys.length === 0) return "空のオブジェクト";
      if (keys.length <= 3) {
        return keys.join(", ");
      }
      return `${keys.length}項目`;
    }
    return String(entry);
  };

  const shouldExpandByDefault = (key: string, entry: JsonValue): boolean => {
    const lowerKey = key.toLowerCase();
    if (COLLAPSED_BY_DEFAULT_KEYS.has(lowerKey)) return false;
    if (EXPANDED_BY_DEFAULT_KEYS.has(lowerKey)) return true;
    // 配列で3要素以下、またはオブジェクトで3キー以下は展開
    if (Array.isArray(entry) && entry.length <= 3) return true;
    if (isJsonObject(entry) && Object.keys(entry).length <= 3) return true;
    return false;
  };

  const renderJsonEditor = useCallback(
    (value: JsonValue, path: Array<string | number> = []) => {
      if (Array.isArray(value)) {
        const primitivesOnly = value.every(isJsonPrimitive);
        if (primitivesOnly) {
          const sample = value.find(item => item !== null);
          const sampleType = typeof sample;
          const inputValue = value
            .map(item => (item === null ? "" : String(item)))
            .filter(item => item.length > 0)
            .join(", ");
          return (
            <input
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm transition focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
              value={inputValue}
              onChange={event => {
                const raw = event.target.value;
                const parts = parseCommaSeparated(raw);
                if (sampleType === "number") {
                  updateParsedJsonValue(
                    path,
                    parts.map(part => {
                      const parsed = Number(part);
                      return Number.isNaN(parsed) ? part : parsed;
                    }),
                  );
                  return;
                }
                if (sampleType === "boolean") {
                  updateParsedJsonValue(
                    path,
                    parts.map(part => {
                      if (part.toLowerCase() === "true") {
                        return true;
                      }
                      if (part.toLowerCase() === "false") {
                        return false;
                      }
                      return part;
                    }),
                  );
                  return;
                }
                updateParsedJsonValue(path, parts);
              }}
              placeholder="カンマ区切りで入力"
            />
          );
        }
        return (
          <div className="space-y-2">
            {value.map((entry, index) => (
              <div
                key={`${path.join(".")}-${index}`}
                className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm"
              >
                <p className="mb-2 text-xs font-semibold text-blue-600">[{index}]</p>
                {renderJsonEditor(entry, [...path, index])}
              </div>
            ))}
          </div>
        );
      }

      if (isJsonObject(value)) {
        return (
          <div className="space-y-4">
            {Object.entries(value).map(([key, entry]) => {
              const isComplex = isJsonObject(entry) || Array.isArray(entry);
              const isImportant = EXPANDED_BY_DEFAULT_KEYS.has(key.toLowerCase());

              return (
                <div
                  key={`${path.join(".")}-${key}`}
                  className={`rounded-lg border p-3 ${
                    isImportant ? "border-blue-200 bg-blue-50/50" : "border-gray-200 bg-gray-50/50"
                  }`}
                >
                  <div
                    className={`mb-2 text-xs font-bold ${
                      isImportant ? "text-blue-700" : "text-gray-600"
                    }`}
                  >
                    {key}
                  </div>
                  <div>
                    {isComplex ? (
                      <details open={shouldExpandByDefault(key, entry)}>
                        <summary className="cursor-pointer select-none rounded-md bg-white px-3 py-2 text-xs font-medium text-gray-700 shadow-sm transition hover:bg-gray-100">
                          <span className="ml-1 text-gray-500">
                            {getSummaryPreview(entry, key)}
                          </span>
                        </summary>
                        <div className="mt-3 pl-2">{renderJsonEditor(entry, [...path, key])}</div>
                      </details>
                    ) : (
                      renderJsonEditor(entry, [...path, key])
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        );
      }

      if (typeof value === "boolean") {
        return (
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-md bg-white px-3 py-2 text-sm shadow-sm">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              checked={value}
              onChange={event => updateParsedJsonValue(path, event.target.checked)}
            />
            <span className={value ? "font-medium text-green-600" : "text-gray-500"}>
              {value ? "true" : "false"}
            </span>
          </label>
        );
      }

      const currentValue = value === null ? "" : String(value);
      return (
        <input
          className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm transition focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
          value={currentValue}
          onChange={event => {
            const raw = event.target.value;
            if (typeof value === "number") {
              if (!raw.trim()) {
                updateParsedJsonValue(path, null);
                return;
              }
              const parsed = Number(raw);
              updateParsedJsonValue(path, Number.isNaN(parsed) ? value : parsed);
              return;
            }
            updateParsedJsonValue(path, raw);
          }}
        />
      );
    },
    [updateParsedJsonValue],
  );

  const handleFormatParsedJson = useCallback(() => {
    if (!formState) {
      return;
    }
    try {
      const parsed = parseJsonInput(formState.parsed_json);
      setFormState(prev =>
        prev
          ? {
              ...prev,
              parsed_json: parsed ? JSON.stringify(parsed, null, 2) : "",
            }
          : prev,
      );
      toast({ title: "JSONを整形しました" });
    } catch (jsonError) {
      toast({
        title: "JSONの整形に失敗しました",
        description: jsonError instanceof Error ? jsonError.message : "不明なエラーです",
        variant: "destructive",
      });
    }
  }, [formState]);

  const handleCopyParsedJson = useCallback(async () => {
    if (!formState?.parsed_json) {
      return;
    }
    try {
      await navigator.clipboard.writeText(formState.parsed_json);
      toast({ title: "JSONをコピーしました" });
    } catch (copyError) {
      toast({
        title: "コピーに失敗しました",
        description: copyError instanceof Error ? copyError.message : "不明なエラーです",
        variant: "destructive",
      });
    }
  }, [formState?.parsed_json]);

  const handleOverrideFieldChange = useCallback(
    <T extends keyof OverrideFormValues>(key: T, value: OverrideFormValues[T]) => {
      setOverrideDialog(prev => ({
        ...prev,
        values: { ...prev.values, [key]: value },
        error: null,
      }));
    },
    [],
  );

  const handleScrapeOfficialUrl = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (!candidate) {
      return;
    }
    if (!formState?.official_url) {
      toast({
        title: "エラー",
        description: "URLを入力してください",
        variant: "destructive",
      });
      return;
    }

    setIsScraping(true);
    try {
      const result = await scrapeCandidateOfficialUrl(candidate.id, formState.official_url, true);

      if (result.parsed_json) {
        setScrapePreview({
          open: true,
          data: result.parsed_json,
        });
        toast({
          title: "スクレイピング完了",
          description: "内容を確認して反映してください",
        });
      } else {
        toast({
          title: "データなし",
          description: "有効なデータが取得できませんでした",
        });
      }
    } catch (err) {
      toast({
        title: "エラー",
        description: err instanceof Error ? err.message : "スクレイピングに失敗しました",
        variant: "destructive",
      });
    } finally {
      setIsScraping(false);
    }
  };

  const handleOverrideSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const { values, mode, baseOverride } = overrideDialog;

      if (mode === "conflict") {
        const trimmedName = values.name.trim();
        if (!trimmedName) {
          setOverrideDialog(prev => ({
            ...prev,
            error: "上書きする名称を入力してください",
          }));
          return;
        }
        const success = await performApproval({
          ...(baseOverride ?? {}),
          name: trimmedName,
        });
        if (success) {
          closeOverrideDialog();
        }
        return;
      }

      const prefSlug = values.pref_slug.trim();
      const citySlug = values.city_slug.trim();
      if (!prefSlug || !citySlug) {
        setOverrideDialog(prev => ({
          ...prev,
          error: "都道府県と市区町村のスラッグを入力してください",
        }));
        return;
      }

      const parseCoordinate = (label: string, input: string) => {
        if (!input.trim()) {
          return undefined;
        }
        const parsed = Number(input);
        if (Number.isNaN(parsed)) {
          throw new Error(`${label} には数値を入力してください`);
        }
        return parsed;
      };

      let latitudeValue: number | undefined;
      let longitudeValue: number | undefined;
      try {
        latitudeValue = parseCoordinate("緯度", values.latitude);
        longitudeValue = parseCoordinate("経度", values.longitude);
      } catch (coordinateError) {
        setOverrideDialog(prev => ({
          ...prev,
          error:
            coordinateError instanceof Error
              ? coordinateError.message
              : "緯度・経度には数値を入力してください",
        }));
        return;
      }

      const success = await performApproval({
        ...(baseOverride ?? {}),
        name: values.name.trim() || baseOverride?.name || undefined,
        pref_slug: prefSlug,
        city_slug: citySlug,
        address: values.address.trim() || baseOverride?.address || undefined,
        latitude: latitudeValue ?? baseOverride?.latitude,
        longitude: longitudeValue ?? baseOverride?.longitude,
        official_url: values.official_url.trim() || baseOverride?.official_url || undefined,
      });

      if (success) {
        closeOverrideDialog();
      }
    },
    [closeOverrideDialog, overrideDialog, performApproval],
  );

  const isLoading = !candidate && !error;

  const renderPreview = useMemo(() => {
    if (!preview.open || !preview.summary) {
      return null;
    }
    const { gym, equipments } = preview.summary;
    return (
      <div className="fixed inset-0 z-[1100] flex items-center justify-center bg-black/50 p-4">
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

  const renderScrapePreview = useMemo(() => {
    if (!scrapePreview.open || !scrapePreview.data) {
      return null;
    }
    return (
      <div className="fixed inset-0 z-[1100] flex items-center justify-center bg-black/50 p-4">
        <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-md bg-white p-6 shadow-lg">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">スクレイピング結果プレビュー</h2>
            <button type="button" className="text-sm text-gray-500" onClick={closeScrapePreview}>
              閉じる
            </button>
          </div>
          <p className="mb-2 text-sm text-gray-600">
            以下の内容で <code>parsed_json</code> を上書きしますか？
            <br />
            反映後、必ず「保存」ボタンを押してください。
          </p>
          <div className="mb-6 rounded border border-gray-200 bg-gray-50 p-4">
            <pre className="overflow-x-auto whitespace-pre-wrap text-xs font-mono">
              {JSON.stringify(scrapePreview.data, null, 2)}
            </pre>
          </div>
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              className="rounded border border-gray-300 px-4 py-2 text-sm"
              onClick={closeScrapePreview}
            >
              キャンセル
            </button>
            <button
              type="button"
              className="rounded bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
              onClick={handleScrapeApply}
            >
              反映する
            </button>
          </div>
        </div>
      </div>
    );
  }, [scrapePreview, closeScrapePreview, handleScrapeApply]);

  const renderOverrideDialog = useMemo(() => {
    if (!overrideDialog.open) {
      return null;
    }
    const isConflictMode = overrideDialog.mode === "conflict";
    return (
      <div className="fixed inset-0 z-[1100] flex items-center justify-center bg-black/50 p-4">
        <div className="w-full max-w-xl rounded-md bg-white p-6 shadow-lg">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">
                {isConflictMode
                  ? "slug の競合を解消してください"
                  : "承認に必要な情報を入力してください"}
              </h2>
              {overrideDialog.message ? (
                <p className="mt-1 text-sm text-gray-600">{overrideDialog.message}</p>
              ) : null}
            </div>
            <button type="button" className="text-sm text-gray-500" onClick={closeOverrideDialog}>
              閉じる
            </button>
          </div>
          <form className="flex flex-col gap-3" onSubmit={handleOverrideSubmit}>
            {isConflictMode ? (
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">新しい名称 *</span>
                <input
                  className="rounded border border-gray-300 px-3 py-2"
                  value={overrideDialog.values.name}
                  onChange={event => handleOverrideFieldChange("name", event.target.value)}
                  required
                />
              </label>
            ) : (
              <>
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="flex flex-col gap-1 text-sm">
                    <span className="font-medium">都道府県スラッグ *</span>
                    <input
                      className="rounded border border-gray-300 px-3 py-2"
                      value={overrideDialog.values.pref_slug}
                      onChange={event => handleOverrideFieldChange("pref_slug", event.target.value)}
                      required
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-sm">
                    <span className="font-medium">市区町村スラッグ *</span>
                    <input
                      className="rounded border border-gray-300 px-3 py-2"
                      value={overrideDialog.values.city_slug}
                      onChange={event => handleOverrideFieldChange("city_slug", event.target.value)}
                      required
                    />
                  </label>
                </div>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="font-medium">名称（必要に応じて上書き）</span>
                  <input
                    className="rounded border border-gray-300 px-3 py-2"
                    value={overrideDialog.values.name}
                    onChange={event => handleOverrideFieldChange("name", event.target.value)}
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="font-medium">住所</span>
                  <textarea
                    className="h-20 rounded border border-gray-300 px-3 py-2"
                    value={overrideDialog.values.address}
                    onChange={event => handleOverrideFieldChange("address", event.target.value)}
                  />
                </label>
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="flex flex-col gap-1 text-sm">
                    <span className="font-medium">緯度</span>
                    <input
                      className="rounded border border-gray-300 px-3 py-2"
                      value={overrideDialog.values.latitude}
                      onChange={event => handleOverrideFieldChange("latitude", event.target.value)}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-sm">
                    <span className="font-medium">経度</span>
                    <input
                      className="rounded border border-gray-300 px-3 py-2"
                      value={overrideDialog.values.longitude}
                      onChange={event => handleOverrideFieldChange("longitude", event.target.value)}
                    />
                  </label>
                </div>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="font-medium">公式サイトURL</span>
                  <input
                    className="rounded border border-gray-300 px-3 py-2"
                    value={overrideDialog.values.official_url}
                    onChange={event =>
                      handleOverrideFieldChange("official_url", event.target.value)
                    }
                  />
                </label>
              </>
            )}
            {overrideDialog.error ? (
              <p className="text-sm text-red-600">{overrideDialog.error}</p>
            ) : null}
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                className="rounded border border-gray-300 px-4 py-2 text-sm"
                onClick={closeOverrideDialog}
                disabled={actionState === "approving"}
              >
                キャンセル
              </button>
              <button
                type="submit"
                className="rounded bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700"
                disabled={actionState === "approving"}
              >
                {actionState === "approving"
                  ? "送信中..."
                  : isConflictMode
                    ? "名称を更新"
                    : "承認を再試行"}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }, [
    closeOverrideDialog,
    handleOverrideFieldChange,
    handleOverrideSubmit,
    overrideDialog,
    actionState,
  ]);

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
            <span className="font-medium">公式サイトURL</span>
            <div className="flex items-center gap-2">
              <input
                className="flex-1 rounded border border-gray-300 px-3 py-2"
                value={formState.official_url}
                onChange={event => handleInputChange("official_url", event.target.value)}
                placeholder="https://..."
              />
              {candidate && (
                <button
                  type="button"
                  onClick={handleScrapeOfficialUrl}
                  disabled={isScraping}
                  className="whitespace-nowrap rounded border border-gray-300 bg-gray-50 px-3 py-2 text-sm hover:bg-gray-100 disabled:opacity-50"
                  title="公式URLから情報を再取得"
                >
                  {isScraping ? "取得中..." : "スクレイプ"}
                </button>
              )}
            </div>
          </label>
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
              <div className="flex gap-2">
                <input
                  className="w-full rounded border border-gray-300 px-3 py-2"
                  value={formState.longitude}
                  onChange={event => handleInputChange("longitude", event.target.value)}
                />
                <button
                  type="button"
                  onClick={async () => {
                    if (!candidate) return;
                    setActionState("saving");
                    try {
                      const updated = await geocodeCandidate(candidate.id, formState?.address_raw);
                      updateCandidateState(updated);
                      toast({ title: "住所検索を実行しました" });
                    } catch (err) {
                      toast({
                        title: "住所検索に失敗しました",
                        description: err instanceof Error ? err.message : "不明なエラー",
                        variant: "destructive",
                      });
                    } finally {
                      setActionState("idle");
                    }
                  }}
                  disabled={actionState !== "idle"}
                  className="whitespace-nowrap rounded bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  住所検索
                </button>
              </div>
            </label>
          </div>
          <div className="flex flex-col gap-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium">解析済みJSON</span>
              <button
                type="button"
                className="rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50"
                onClick={() => setIsRawJsonVisible(prev => !prev)}
              >
                {isRawJsonVisible ? "JSONを隠す" : "JSONを直接編集"}
              </button>
            </div>
            <div className="rounded border border-gray-200 bg-gray-50 p-3">
              <p className="mb-2 text-xs text-gray-600">
                項目ごとに編集できます。配列はカンマ区切りで入力してください。
              </p>
              {parsedJsonError ? (
                <p className="text-xs text-red-600">
                  JSONにエラーがあります。下のJSON編集で修正してください: {parsedJsonError}
                </p>
              ) : (
                <div className="space-y-2">
                  {isParsedJsonEmpty ? (
                    <p className="text-xs text-gray-500">
                      まだJSONがありません。必要な項目があれば下のJSON編集で追加できます。
                    </p>
                  ) : null}
                  {renderJsonEditor(parsedJsonValue)}
                </div>
              )}
            </div>
            {isRawJsonVisible ? (
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <button
                    type="button"
                    className="rounded border border-gray-300 px-2 py-1 hover:bg-gray-50"
                    onClick={() => setIsParsedJsonExpanded(prev => !prev)}
                  >
                    {isParsedJsonExpanded ? "縮小" : "拡大"}
                  </button>
                  <button
                    type="button"
                    className="rounded border border-gray-300 px-2 py-1 hover:bg-gray-50"
                    onClick={handleFormatParsedJson}
                  >
                    整形
                  </button>
                  <button
                    type="button"
                    className="rounded border border-gray-300 px-2 py-1 hover:bg-gray-50"
                    onClick={() => void handleCopyParsedJson()}
                    disabled={!formState.parsed_json.trim()}
                  >
                    コピー
                  </button>
                </div>
                <textarea
                  className={`rounded border px-3 py-2 font-mono text-xs ${
                    parsedJsonError ? "border-red-400" : "border-gray-300"
                  } ${isParsedJsonExpanded ? "h-96" : "h-52"}`}
                  value={formState.parsed_json}
                  onChange={event => handleInputChange("parsed_json", event.target.value)}
                />
                {parsedJsonError ? (
                  <p className="text-xs text-red-600">JSONエラー: {parsedJsonError}</p>
                ) : (
                  <p className="text-xs text-gray-500">JSON形式は正常です</p>
                )}
              </div>
            ) : null}
          </div>
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
            <h2 className="text-lg font-semibold mb-3">地図</h2>
            <div className="rounded-lg overflow-hidden">
              <GymMap
                name={formState.name_raw}
                address={formState.address_raw}
                latitude={formState.latitude ? Number(formState.latitude) : undefined}
                longitude={formState.longitude ? Number(formState.longitude) : undefined}
                prefecture={formState.pref_slug}
                city={formState.city_slug}
              />
            </div>
          </section>
          <section className="rounded border border-gray-200 p-4 shadow-sm">
            <h2 className="text-lg font-semibold">スクレイプ情報</h2>
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="font-medium">Official URL</dt>
                <dd>
                  {candidate.official_url ? (
                    <a
                      className="text-blue-600 underline"
                      href={candidate.official_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {candidate.official_url}
                    </a>
                  ) : (
                    "-"
                  )}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">Source URL</dt>
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
      {renderOverrideDialog}
      {renderScrapePreview}
    </Fragment>
  );
}
