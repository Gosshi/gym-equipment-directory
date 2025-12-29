"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { BookmarkCheck, BookmarkPlus } from "lucide-react";

import { CategoryInfo } from "@/components/gym/CategoryInfo";
import { GymFacilities, type FacilityGroup } from "@/components/gym/GymFacilities";
import { GymHeader } from "@/components/gym/GymHeader";
import { ReportIssueButton } from "@/components/gym/ReportIssueButton";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { AdBanner } from "@/components/ads/AdBanner";
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

import { type NormalizedGymDetail, normalizeGymDetail, sanitizeText } from "./normalization";

type FetchStatus = "idle" | "loading" | "success" | "error";

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
  initialGym,
  onCanonicalSlugChange,
}: {
  slug: string;
  initialGym?: NormalizedGymDetail;
  onCanonicalSlugChange?: (nextSlug: string) => void;
}) {
  const [status, setStatus] = useState<FetchStatus>(initialGym ? "success" : "idle");
  const [gym, setGym] = useState<NormalizedGymDetail | null>(initialGym ?? null);
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
    if (initialGym) {
      return;
    }
    loadGym();

    return () => {
      abortControllerRef.current?.abort();
    };
  }, [loadGym, initialGym]);

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
        {/* Breadcrumbs with gym name */}
        <Breadcrumbs
          items={[
            { label: "ジム検索", href: "/gyms" },
            { label: gym.name, href: `/gyms/${gym.slug}`, current: true },
          ]}
        />

        <GymHeader
          gymId={gym.id}
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
          tags={gym.tags}
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

            <CategoryInfo
              category={gym.category}
              categories={gym.categories}
              poolLanes={gym.poolLanes}
              poolLengthM={gym.poolLengthM}
              poolHeated={gym.poolHeated}
              courtType={gym.courtType}
              courtCount={gym.courtCount}
              courtSurface={gym.courtSurface}
              courtLighting={gym.courtLighting}
              hallSports={gym.hallSports}
              hallAreaSqm={gym.hallAreaSqm}
              fieldType={gym.fieldType}
              fieldCount={gym.fieldCount}
              fieldLighting={gym.fieldLighting}
            />

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

            <div className="mt-6">
              <AdBanner slotId="YOUR_SLOT_ID_HERE" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
