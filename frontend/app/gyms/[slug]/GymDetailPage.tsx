"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { BookmarkCheck, BookmarkPlus } from "lucide-react";

import { GymFacilities, type FacilityGroup } from "@/components/gym/GymFacilities";
import { GymHeader } from "@/components/gym/GymHeader";
import { ReportIssueButton } from "@/components/gym/ReportIssueButton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { ApiError, apiRequest } from "@/lib/apiClient";
import { encodeOnce } from "@/lib/url";
import type {
  GymDetailApiResponse,
  GymEquipmentDetailApiResponse,
  GymFacilityCategoryApiResponse,
  GymLocationApiResponse,
} from "@/types/api";

import { GymDetailError } from "./GymDetailError";

const GymMap = dynamic(() => import("@/components/gym/GymMap").then(module => module.GymMap), {
  loading: () => (
    <Card>
      <CardHeader>
        <CardTitle>地図</CardTitle>
        <CardDescription>所在地の確認やルート検索にご利用ください。</CardDescription>
      </CardHeader>
      <CardContent>
        <Skeleton className="aspect-[4/3] w-full rounded-lg" />
      </CardContent>
    </Card>
  ),
  ssr: false,
});

interface NormalizedGymDetail {
  slug: string;
  name: string;
  description?: string;
  address?: string;
  prefecture?: string;
  city?: string;
  categories: string[];
  openingHours?: string;
  fees?: string;
  website?: string;
  facilities: FacilityGroup[];
  latitude?: number;
  longitude?: number;
}

type FetchStatus = "idle" | "loading" | "success" | "error";

const sanitizeText = (value: unknown): string | undefined => {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
};

const formatRegion = (value?: string | null): string | undefined => {
  const sanitized = sanitizeText(value);
  if (!sanitized) {
    return undefined;
  }

  return sanitized
    .split("-")
    .map(part => (part ? part.charAt(0).toUpperCase() + part.slice(1) : part))
    .join(" ");
};

const extractCategoryNames = (input: unknown): string[] => {
  const result: string[] = [];
  const seen = new Set<string>();

  const add = (value?: string) => {
    if (!value) {
      return;
    }
    if (seen.has(value)) {
      return;
    }
    seen.add(value);
    result.push(value);
  };

  const visit = (value: unknown) => {
    if (!value) {
      return;
    }
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (typeof value === "string") {
      add(sanitizeText(value));
      return;
    }
    if (typeof value === "object") {
      const record = value as Record<string, unknown>;
      const label =
        sanitizeText(record.name) ??
        sanitizeText(record.label) ??
        sanitizeText(record.title) ??
        sanitizeText(record.slug);

      if (label) {
        add(label);
        return;
      }

      for (const nested of Object.values(record)) {
        visit(nested);
      }
    }
  };

  visit(input);
  return result;
};

const extractFacilityItems = (input: unknown): string[] => {
  if (!input) {
    return [];
  }
  if (Array.isArray(input)) {
    const collected: string[] = [];
    for (const item of input) {
      collected.push(...extractFacilityItems(item));
    }
    return collected;
  }
  if (typeof input === "string") {
    const sanitized = sanitizeText(input);
    return sanitized ? [sanitized] : [];
  }
  if (typeof input === "object") {
    const record = input as Record<string, unknown>;
    const label =
      sanitizeText(record.name) ??
      sanitizeText(record.label) ??
      sanitizeText(record.title) ??
      sanitizeText(record.value) ??
      sanitizeText(record.slug);

    const results: string[] = [];
    if (label) {
      results.push(label);
    }

    const nestedKeys = [
      "items",
      "equipments",
      "equipment_details",
      "equipmentDetails",
      "values",
      "list",
    ];
    for (const key of nestedKeys) {
      if (record[key] !== undefined) {
        results.push(...extractFacilityItems(record[key]));
      }
    }

    return results;
  }
  return [];
};

const extractFacilityGroups = (data: GymDetailApiResponse): FacilityGroup[] => {
  const groups = new Map<string, { items: string[]; set: Set<string> }>();

  const ensureGroup = (category?: string | null) => {
    const label = sanitizeText(category) ?? "設備";
    const key = label.length > 0 ? label : "設備";
    if (!groups.has(key)) {
      groups.set(key, { items: [], set: new Set<string>() });
    }
    return groups.get(key)!;
  };

  const addItemsToGroup = (category: string | null | undefined, values: string[]) => {
    if (values.length === 0) {
      return;
    }
    const group = ensureGroup(category);
    for (const value of values) {
      const sanitized = sanitizeText(value);
      if (!sanitized || group.set.has(sanitized)) {
        continue;
      }
      group.set.add(sanitized);
      group.items.push(sanitized);
    }
  };

  const visitCategoryEntry = (entry: unknown) => {
    if (!entry) {
      return;
    }
    if (Array.isArray(entry)) {
      entry.forEach(visitCategoryEntry);
      return;
    }
    if (typeof entry === "string") {
      addItemsToGroup("設備", [entry]);
      return;
    }
    if (typeof entry === "object") {
      const record = entry as GymFacilityCategoryApiResponse & Record<string, unknown>;
      const category =
        record.category ?? record.name ?? record.label ?? record.title ?? record.group ?? undefined;

      const aggregated: string[] = [];
      if (record.items !== undefined) {
        aggregated.push(...extractFacilityItems(record.items));
      }
      if (record.equipments !== undefined) {
        aggregated.push(...extractFacilityItems(record.equipments));
      }
      if (record.equipment_details !== undefined) {
        aggregated.push(...extractFacilityItems(record.equipment_details));
      }
      if (aggregated.length === 0) {
        const fallback = sanitizeText(record.name) ?? sanitizeText(record.label);
        if (fallback) {
          aggregated.push(fallback);
        }
      }

      addItemsToGroup(category, aggregated);
      return;
    }
  };

  visitCategoryEntry(data.facilities);
  visitCategoryEntry(data.facility_groups);

  const equipmentDetails = data.equipment_details;
  if (Array.isArray(equipmentDetails)) {
    for (const item of equipmentDetails) {
      if (!item) {
        continue;
      }
      if (typeof item === "string") {
        addItemsToGroup("設備", [item]);
        continue;
      }
      if (typeof item === "object") {
        const record = item as GymEquipmentDetailApiResponse & Record<string, unknown>;
        const category = record.category ?? record.group ?? record.type ?? undefined;
        const label =
          sanitizeText(record.name) ?? sanitizeText(record.label) ?? sanitizeText(record.title);
        const nested = extractFacilityItems(record.items);
        const combined = [...(label ? [label] : []), ...nested];
        addItemsToGroup(category, combined);
      }
    }
  } else if (equipmentDetails) {
    addItemsToGroup("設備", extractFacilityItems(equipmentDetails));
  }

  if (data.equipments) {
    addItemsToGroup("設備", extractFacilityItems(data.equipments));
  }

  const result: FacilityGroup[] = [];
  for (const [category, { items }] of groups.entries()) {
    if (items.length > 0) {
      result.push({ category, items });
    }
  }
  return result;
};

const normalizeGymDetail = (
  data: GymDetailApiResponse,
  canonicalSlug: string,
): NormalizedGymDetail => {
  const categories = extractCategoryNames(data.categories ?? data.facilities ?? []);
  const facilities = extractFacilityGroups(data);
  const gymRecord = (data.gym ?? {}) as Record<string, unknown>;
  const locationSource =
    data.location ?? (gymRecord.location as GymLocationApiResponse | null | undefined);
  const location = locationSource ?? null;

  const pickNumber = (...values: unknown[]): number | undefined => {
    for (const value of values) {
      if (typeof value === "number" && Number.isFinite(value)) {
        return value;
      }
      if (typeof value === "string") {
        const parsed = Number(value);
        if (!Number.isNaN(parsed)) {
          return parsed;
        }
      }
    }
    return undefined;
  };

  const latitude = pickNumber(
    data.latitude,
    data.lat,
    gymRecord.latitude,
    gymRecord.lat,
    location?.latitude,
    location?.lat,
  );
  const longitude = pickNumber(
    data.longitude,
    data.lng,
    gymRecord.longitude,
    gymRecord.lng,
    location?.longitude,
    location?.lng,
  );

  const resolvedName = sanitizeText(data.name) ?? sanitizeText(gymRecord.name) ?? canonicalSlug;
  const resolvedAddress =
    sanitizeText(data.address) ??
    sanitizeText(gymRecord.address) ??
    sanitizeText(location?.address);
  const resolvedPref =
    sanitizeText(data.prefecture ?? data.pref) ??
    sanitizeText(gymRecord.pref ?? gymRecord.prefecture);
  const resolvedCity = sanitizeText(data.city) ?? sanitizeText(gymRecord.city);
  const resolvedWebsite = sanitizeText(data.website ?? data.website_url);

  return {
    slug: canonicalSlug,
    name: resolvedName,
    description: sanitizeText(data.description),
    address: resolvedAddress,
    prefecture: formatRegion(resolvedPref),
    city: formatRegion(resolvedCity),
    categories,
    openingHours: sanitizeText(data.openingHours ?? data.opening_hours),
    fees: sanitizeText(data.fees ?? data.price),
    website: resolvedWebsite,
    facilities,
    latitude,
    longitude,
  };
};

interface FetchGymDetailResult {
  normalized: NormalizedGymDetail;
  canonicalSlug: string;
  requestedSlug: string;
  shouldRedirect: boolean;
}

async function fetchGymDetail(slug: string, signal?: AbortSignal): Promise<FetchGymDetailResult> {
  const response = await apiRequest<GymDetailApiResponse>(`/gyms/${encodeOnce(slug)}`, {
    method: "GET",
    signal,
  });

  const gymRecord = (response.gym ?? {}) as Record<string, unknown>;
  const canonicalSlug =
    sanitizeText(response.canonical_slug) ??
    sanitizeText(response.slug) ??
    sanitizeText(gymRecord.slug) ??
    slug;
  const requestedSlug = sanitizeText(response.requested_slug) ?? slug;
  const normalized = normalizeGymDetail(response, canonicalSlug);
  const shouldRedirect = Boolean(response.meta?.redirect) || canonicalSlug !== requestedSlug;

  return { normalized, canonicalSlug, requestedSlug, shouldRedirect };
}

const GymDetailSkeleton = () => (
  <div className="flex min-h-screen flex-col px-4 py-10">
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
      <section className="space-y-6">
        <div className="space-y-3">
          <Skeleton className="h-10 w-48" />
          <Skeleton className="h-4 w-72" />
          <Skeleton className="h-4 w-48" />
        </div>
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton className="h-6 w-20 rounded-full" key={index} />
          ))}
        </div>
        <div className="flex flex-wrap gap-3">
          <Skeleton className="h-10 w-36 rounded-md" />
          <Skeleton className="h-10 w-36 rounded-md" />
        </div>
      </section>
      <Skeleton className="h-[1px] w-full" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="space-y-6">
          <Skeleton className="h-56 w-full rounded-lg" />
          <Skeleton className="h-72 w-full rounded-lg" />
        </div>
        <div className="space-y-6">
          <Skeleton className="h-72 w-full rounded-lg" />
        </div>
      </div>
    </div>
  </div>
);

export function GymDetailPage({
  slug,
  onCanonicalSlugChange,
}: {
  slug: string;
  onCanonicalSlugChange?: (nextSlug: string) => void;
}) {
  const [status, setStatus] = useState<FetchStatus>("idle");
  const [gym, setGym] = useState<NormalizedGymDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isFavorite, setIsFavorite] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const { toast } = useToast();
  const router = useRouter();

  const loadGym = useCallback(() => {
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setStatus("loading");
    setErrorMessage(null);

    fetchGymDetail(slug, controller.signal)
      .then(result => {
        if (controller.signal.aborted) {
          return;
        }
        setGym(result.normalized);
        setStatus("success");
        onCanonicalSlugChange?.(result.canonicalSlug);
        if (result.shouldRedirect && result.canonicalSlug) {
          router.replace(`/gyms/${encodeOnce(result.canonicalSlug)}`);
        }
      })
      .catch(error => {
        if (controller.signal.aborted) {
          return;
        }

        let message = "ジム情報の取得に失敗しました。時間をおいて再度お試しください。";
        if (error instanceof ApiError) {
          if (error.status === 404) {
            message = "指定されたジムが見つかりませんでした。";
          } else {
            const statusLabel = error.status ? ` (status: ${error.status})` : "";
            message = `ジム情報の取得中にエラーが発生しました${statusLabel}`;
          }
        } else if (error instanceof Error && error.message) {
          message = error.message;
        }

        setErrorMessage(message);
        setStatus("error");
      });
  }, [slug, onCanonicalSlugChange, router]);

  useEffect(() => {
    loadGym();

    return () => {
      abortControllerRef.current?.abort();
    };
  }, [loadGym]);

  useEffect(() => {
    setIsFavorite(false);
  }, [slug]);

  const handleToggleFavorite = useCallback(() => {
    if (!gym) {
      return;
    }

    setIsFavorite(previous => {
      const next = !previous;
      toast({
        title: next ? "お気に入りに追加しました" : "お気に入りから削除しました",
        description: next
          ? `${gym.name} をお気に入りに追加しました。`
          : `${gym.name} をお気に入りから削除しました。`,
      });
      return next;
    });
  }, [gym, toast]);

  if (status === "loading" || status === "idle") {
    return <GymDetailSkeleton />;
  }

  if (status === "error" || !gym) {
    return (
      <GymDetailError
        message={errorMessage ?? "ジム情報を読み込めませんでした。"}
        onRetry={loadGym}
      />
    );
  }

  const locationParts = [gym.prefecture, gym.city].filter(Boolean);
  const locationLabel = locationParts.length > 0 ? locationParts.join(" / ") : undefined;

  const FavoriteIcon = isFavorite ? BookmarkCheck : BookmarkPlus;
  const favoriteLabel = isFavorite ? "お気に入り済み" : "お気に入りに追加";

  return (
    <div className="flex min-h-screen flex-col px-4 py-10">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
        <GymHeader
          actions={
            <div className="flex flex-wrap gap-3">
              <ReportIssueButton gymName={gym.name} slug={gym.slug} />
              <Button
                aria-pressed={isFavorite}
                disabled={status !== "success"}
                onClick={handleToggleFavorite}
                type="button"
                variant={isFavorite ? "secondary" : "default"}
              >
                <FavoriteIcon aria-hidden className="mr-2 h-4 w-4" />
                {favoriteLabel}
              </Button>
            </div>
          }
          address={gym.address}
          categories={gym.categories}
          locationLabel={locationLabel}
          name={gym.name}
        />

        <Separator />

        <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>基本情報</CardTitle>
                <CardDescription>
                  営業時間や料金、公式サイトへの導線をまとめています。
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  {gym.description ? (
                    <p className="text-sm leading-relaxed text-foreground/90">{gym.description}</p>
                  ) : (
                    <p className="text-sm text-muted-foreground">紹介文は現在準備中です。</p>
                  )}
                </div>
                <dl className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1">
                    <dt className="text-sm font-medium text-muted-foreground">営業時間</dt>
                    <dd className="text-sm text-foreground">
                      {gym.openingHours ?? "営業時間情報はまだ登録されていません。"}
                    </dd>
                  </div>
                  <div className="space-y-1">
                    <dt className="text-sm font-medium text-muted-foreground">料金</dt>
                    <dd className="text-sm text-foreground">
                      {gym.fees ?? "料金情報はまだ登録されていません。"}
                    </dd>
                  </div>
                  <div className="space-y-1 sm:col-span-2">
                    <dt className="text-sm font-medium text-muted-foreground">公式サイト</dt>
                    <dd>
                      {gym.website ? (
                        <a
                          className="text-sm font-medium text-primary underline-offset-4 hover:underline"
                          href={gym.website}
                          rel="noopener noreferrer"
                          target="_blank"
                        >
                          公式サイトを見る
                        </a>
                      ) : (
                        <span className="text-sm text-muted-foreground">
                          公式サイト情報は未登録です。
                        </span>
                      )}
                    </dd>
                  </div>
                </dl>
              </CardContent>
            </Card>

            <GymFacilities facilities={gym.facilities} />
          </div>

          <div className="space-y-6">
            <GymMap
              address={gym.address}
              latitude={gym.latitude}
              longitude={gym.longitude}
              name={gym.name}
              prefecture={gym.prefecture}
              city={gym.city}
              slug={gym.slug}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
