"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/apiClient";
import { cn } from "@/lib/utils";
import { addFavorite, removeFavorite } from "@/services/favorites";
import { getGymBySlug } from "@/services/gyms";
import type { GymDetail } from "@/types/gym";
import { useFavoriteGyms } from "@/store/favorites";

type FetchStatus = "idle" | "loading" | "success" | "error";

const formatRegion = (value?: string | null) => {
  if (!value) {
    return undefined;
  }

  return value
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

const GymDetailSkeleton = () => (
  <div className="flex min-h-screen flex-col gap-6 px-4 py-10">
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <div className="space-y-4">
        <div className="flex items-center gap-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-40" />
        </div>
        <Skeleton className="h-5 w-40" />
      </div>
      <Skeleton className="h-64 w-full" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Card className="border-none shadow-none">
          <CardContent className="space-y-4 pt-6">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </CardContent>
        </Card>
        <Card className="border-none shadow-none">
          <CardContent className="space-y-4 pt-6">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-10 w-full" />
            <div className="flex gap-2">
              <Skeleton className="h-6 w-20 rounded-full" />
              <Skeleton className="h-6 w-20 rounded-full" />
              <Skeleton className="h-6 w-20 rounded-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
);

const GymDetailError = ({ message, onRetry }: { message: string; onRetry: () => void }) => (
  <div className="flex min-h-screen flex-col px-4 py-10">
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 text-center">
      <div className="space-y-4 rounded-lg border bg-card p-8 shadow-sm">
        <h1 className="text-2xl font-semibold">ジム情報を読み込めませんでした</h1>
        <p className="text-muted-foreground">{message}</p>
        <div className="flex flex-col gap-2">
          <Button onClick={onRetry} type="button">
            再試行する
          </Button>
        </div>
      </div>
    </div>
  </div>
);

export function GymDetailPage({ slug }: { slug: string }) {
  const [status, setStatus] = useState<FetchStatus>("idle");
  const [gym, setGym] = useState<GymDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [favoriteFeedback, setFavoriteFeedback] = useState<string | null>(null);
  const [favoriteError, setFavoriteError] = useState<string | null>(null);
  const [isFavoritePending, setIsFavoritePending] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const { addFavoriteId, removeFavoriteId, isFavorite } = useFavoriteGyms();

  const loadGym = useCallback(() => {
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setStatus("loading");
    setErrorMessage(null);
    setFavoriteFeedback(null);
    setFavoriteError(null);

    getGymBySlug(slug, { signal: controller.signal })
      .then((response) => {
        if (controller.signal.aborted) {
          return;
        }

        setGym(response);
        setStatus("success");
      })
      .catch((error) => {
        if (controller.signal.aborted) {
          return;
        }

        let message = "ジム情報の取得に失敗しました。時間をおいて再度お試しください。";

        if (error instanceof ApiError) {
          if (error.status === 404) {
            message = "指定されたジムが見つかりませんでした。";
          } else {
            message = `ジム情報の取得中にエラーが発生しました (status: ${error.status ?? "unknown"})`;
          }
        }

        setErrorMessage(message);
        setStatus("error");
      });
  }, [slug]);

  useEffect(() => {
    loadGym();

    return () => {
      abortControllerRef.current?.abort();
    };
  }, [loadGym]);

  const handleToggleFavorite = useCallback(async () => {
    if (!gym) {
      return;
    }

    setFavoriteFeedback(null);
    setFavoriteError(null);
    setIsFavoritePending(true);

    try {
      if (isFavorite(gym.id)) {
        await removeFavorite(gym.id);
        removeFavoriteId(gym.id);
        setFavoriteFeedback("お気に入りから削除しました。");
      } else {
        await addFavorite(gym.id);
        addFavoriteId(gym.id);
        setFavoriteFeedback("お気に入りに追加しました。");
      }
    } catch (error) {
      let message = "お気に入りの更新に失敗しました。もう一度お試しください。";

      if (error instanceof ApiError) {
        if (error.status === 404) {
          message = "このジムは現在利用できません。";
        }
      }

      setFavoriteError(message);
    } finally {
      setIsFavoritePending(false);
    }
  }, [addFavoriteId, gym, isFavorite, removeFavoriteId]);

  const locationLabel = useMemo(() => {
    if (!gym) {
      return "";
    }

    const prefecture = formatRegion(gym.prefecture);
    const city = formatRegion(gym.city);

    if (prefecture && city) {
      return `${prefecture} / ${city}`;
    }

    return prefecture ?? city ?? "エリア情報未設定";
  }, [gym]);

  if (status === "loading" || status === "idle") {
    return <GymDetailSkeleton />;
  }

  if (status === "error" || !gym) {
    return <GymDetailError message={errorMessage ?? "不明なエラーです。"} onRetry={loadGym} />;
  }

  const favoriteActive = isFavorite(gym.id);
  const heroImage = gym.images?.[0] ?? gym.thumbnailUrl ?? undefined;

  return (
    <div className="flex min-h-screen flex-col gap-6 px-4 py-10">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
        <div className="space-y-2">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-2">
              <h1 className="text-3xl font-bold tracking-tight text-foreground">{gym.name}</h1>
              <p className="text-sm text-muted-foreground">{locationLabel}</p>
              {gym.address ? <p className="text-sm text-muted-foreground">{gym.address}</p> : null}
            </div>
            <div className="flex flex-col items-start gap-2 sm:items-end">
              <Button
                aria-pressed={favoriteActive}
                className={cn(
                  "flex items-center gap-2",
                  favoriteActive ? "bg-amber-500 text-amber-900 hover:bg-amber-500/90" : undefined,
                )}
                disabled={isFavoritePending}
                onClick={handleToggleFavorite}
                type="button"
                variant={favoriteActive ? "secondary" : "outline"}
              >
                <span aria-hidden>{favoriteActive ? "★" : "☆"}</span>
                <span>{favoriteActive ? "お気に入り済み" : "☆ お気に入り"}</span>
              </Button>
              <div aria-live="polite" className="text-xs text-muted-foreground min-h-[1.25rem]">
                {favoriteError ? <span className="text-destructive">{favoriteError}</span> : favoriteFeedback}
              </div>
            </div>
          </div>
        </div>

        <div>
          {heroImage ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              alt={`${gym.name} の外観写真`}
              className="h-64 w-full rounded-lg object-cover"
              src={heroImage}
            />
          ) : (
            <div className="flex h-64 w-full items-center justify-center rounded-lg bg-muted text-sm text-muted-foreground">
              表示可能な画像がまだありません。
            </div>
          )}
        </div>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <section>
            <Card>
              <CardHeader>
                <CardTitle>基本情報</CardTitle>
                <CardDescription>
                  営業時間や連絡先など、現時点で取得できる情報を表示します。
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {gym.description ? <p className="text-sm leading-relaxed">{gym.description}</p> : null}
                <dl className="grid gap-3 text-sm md:grid-cols-2">
                  <div>
                    <dt className="font-medium text-foreground">営業時間</dt>
                    <dd className="text-muted-foreground">
                      {gym.openingHours ?? "営業時間情報は準備中です。"}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-medium text-foreground">電話番号</dt>
                    <dd className="text-muted-foreground">{gym.phone ?? "未登録"}</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>
          </section>

          <aside className="space-y-6">
            <section>
              <Card>
                <CardHeader>
                  <CardTitle>設備</CardTitle>
                  <CardDescription>ジムから提供されている代表的な設備一覧です。</CardDescription>
                </CardHeader>
                <CardContent>
                  {gym.equipments.length > 0 ? (
                    <div className="flex flex-wrap gap-2" role="list">
                      {gym.equipments.map((equipment) => (
                        <span
                          key={equipment}
                          className="rounded-full bg-secondary px-3 py-1 text-xs text-secondary-foreground"
                          role="listitem"
                        >
                          {equipment}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">設備情報は現在調査中です。</p>
                  )}
                </CardContent>
              </Card>
            </section>

            {gym.website ? (
              <section>
                <Card>
                  <CardHeader>
                    <CardTitle>公式サイト</CardTitle>
                    <CardDescription>最新情報は公式サイトでご確認ください。</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button asChild type="button">
                      <Link href={gym.website} rel="noreferrer" target="_blank">
                        公式サイトを開く
                      </Link>
                    </Button>
                  </CardContent>
                </Card>
              </section>
            ) : null}
          </aside>
        </div>
      </div>
    </div>
  );
}
