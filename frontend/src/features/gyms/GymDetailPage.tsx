"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { GymDetailHeader } from "@/components/gyms/GymDetailHeader";
import { GymEquipmentTabs } from "@/components/gyms/GymEquipmentTabs";
import { GymImageGallery } from "@/components/gyms/GymImageGallery";
import { GymMapPlaceholder } from "@/components/gyms/GymMapPlaceholder";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/use-toast";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/apiClient";
import { getGymBySlug } from "@/services/gyms";
import type { GymDetail, GymEquipmentDetail } from "@/types/gym";
import { historyStore } from "@/store/historyStore";
import { useFavorites } from "@/store/favoritesStore";
import { useAuthGuard } from "@/routes/withAuthGuard";

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
  <div className="flex min-h-screen flex-col px-4 py-10">
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <div className="space-y-4">
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-56" />
          <Skeleton className="h-4 w-40" />
        </div>
        <Skeleton className="h-4 w-72" />
      </div>
      <Skeleton className="aspect-[16/9] w-full rounded-lg" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] xl:grid-cols-[minmax(0,5fr)_minmax(0,3fr)]">
        <div className="space-y-4">
          <Card className="border-none shadow-none">
            <CardHeader className="space-y-2">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-4 w-56" />
            </CardHeader>
            <CardContent className="space-y-4 pt-0">
              <div className="flex flex-wrap gap-2">
                <Skeleton className="h-7 w-24 rounded-full" />
                <Skeleton className="h-7 w-20 rounded-full" />
                <Skeleton className="h-7 w-28 rounded-full" />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Skeleton className="h-24 rounded-lg" />
                <Skeleton className="h-24 rounded-lg" />
                <Skeleton className="h-24 rounded-lg" />
                <Skeleton className="h-24 rounded-lg" />
              </div>
            </CardContent>
          </Card>
        </div>
        <div className="space-y-4">
          <Card className="border-none shadow-none">
            <CardHeader className="space-y-2">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-4 w-64" />
            </CardHeader>
            <CardContent className="space-y-4 pt-0">
              <Skeleton className="h-4 w-full" />
              <div className="grid gap-3 text-sm md:grid-cols-2">
                <div className="space-y-2">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-full" />
                </div>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-32" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-none shadow-none">
            <CardHeader className="space-y-2">
              <Skeleton className="h-5 w-28" />
              <Skeleton className="h-4 w-40" />
            </CardHeader>
            <CardContent className="pt-0">
              <Skeleton className="h-48 w-full rounded-md" />
            </CardContent>
          </Card>
        </div>
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
  const abortControllerRef = useRef<AbortController | null>(null);

  const {
    addFavorite: addFavoriteGym,
    removeFavorite: removeFavoriteGym,
    isFavorite,
    isPending,
    status: favoritesStatus,
    error: favoritesError,
  } = useFavorites();

  const loadGym = useCallback(() => {
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setStatus("loading");
    setErrorMessage(null);

    getGymBySlug(slug, { signal: controller.signal })
      .then((response) => {
        if (controller.signal.aborted) {
          return;
        }

        setGym(response);
        void historyStore
          .getState()
          .add(response)
          .catch(() => {
            // 履歴更新の失敗は UI を妨げないため握りつぶす
          });
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

  const toggleFavorite = useCallback(async () => {
    if (!gym) {
      return;
    }

    try {
      const wasFavorite = isFavorite(gym.id);
      if (wasFavorite) {
        await removeFavoriteGym(gym.id);
        toast({
          title: "お気に入りから削除しました",
          description: `${gym.name} をお気に入りから解除しました。`,
        });
      } else {
        await addFavoriteGym(gym);
        toast({
          title: "お気に入りに追加しました",
          description: `${gym.name} をお気に入りに登録しました。`,
        });
      }
    } catch (error) {
      let message = "お気に入りの更新に失敗しました。もう一度お試しください。";

      if (error instanceof ApiError && error.status === 404) {
        message = "このジムは現在利用できません。";
      } else if (error instanceof Error && error.message) {
        message = error.message;
      }

      toast({
        title: "お気に入りの更新に失敗しました",
        description: message,
        variant: "destructive",
      });
    }
  }, [addFavoriteGym, gym, isFavorite, removeFavoriteGym]);

  const handleToggleFavorite = useAuthGuard(toggleFavorite);

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

  const galleryImages = useMemo(() => {
    if (!gym) {
      return [] as string[];
    }

    if (gym.images && gym.images.length > 0) {
      return gym.images;
    }

    if (gym.thumbnailUrl) {
      return [gym.thumbnailUrl];
    }

    return [] as string[];
  }, [gym]);

  const equipmentItems = useMemo<GymEquipmentDetail[]>(() => {
    if (!gym) {
      return [];
    }

    if (gym.equipmentDetails && gym.equipmentDetails.length > 0) {
      return gym.equipmentDetails
        .filter((item): item is GymEquipmentDetail => {
          if (!item) {
            return false;
          }
          const name = typeof item.name === "string" ? item.name.trim() : "";
          return name.length > 0;
        })
        .map((item) => {
          const name = item.name.trim();
          const category =
            typeof item.category === "string" && item.category.trim().length > 0
              ? item.category.trim()
              : undefined;
          const description =
            typeof item.description === "string" && item.description.trim().length > 0
              ? item.description.trim()
              : undefined;

          return {
            ...item,
            name,
            category,
            description,
          };
        });
    }

    if (gym.equipments.length > 0) {
      return gym.equipments
        .filter((name): name is string => typeof name === "string" && name.trim().length > 0)
        .map((name, index) => ({
          id: `legacy-${index}`,
          name: name.trim(),
        }));
    }

    return [];
  }, [gym]);

  if (status === "loading" || status === "idle") {
    return <GymDetailSkeleton />;
  }

  if (status === "error" || !gym) {
    return <GymDetailError message={errorMessage ?? "不明なエラーです。"} onRetry={loadGym} />;
  }

  const favoriteActive = isFavorite(gym.id);
  const favoritePending = isPending(gym.id);
  const favoriteDisabled = favoritesStatus === "loading" || favoritesStatus === "idle";

  return (
    <div className="flex min-h-screen flex-col px-4 py-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
        <GymDetailHeader
          address={gym.address ?? undefined}
          favoriteActive={favoriteActive}
          favoriteDisabled={favoriteDisabled}
          favoriteError={favoritesError}
          favoritePending={favoritePending}
          locationLabel={locationLabel}
          name={gym.name}
          onToggleFavorite={handleToggleFavorite}
          website={gym.website ?? undefined}
        />

        <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] xl:grid-cols-[minmax(0,5fr)_minmax(0,3fr)]">
          <div className="space-y-6">
            <GymImageGallery images={galleryImages} name={gym.name} />
            <GymEquipmentTabs equipments={equipmentItems} />
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>基本情報</CardTitle>
                <CardDescription>
                  営業時間や連絡先など、取得済みの最新情報をまとめています。
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {gym.description ? (
                  <p className="text-sm leading-relaxed text-foreground/80">{gym.description}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">紹介文は現在準備中です。</p>
                )}
                <dl className="grid gap-3 text-sm md:grid-cols-2">
                  <div className="space-y-1">
                    <dt className="font-medium text-foreground">営業時間</dt>
                    <dd className="text-muted-foreground">
                      {gym.openingHours ?? "営業時間情報は準備中です。"}
                    </dd>
                  </div>
                  <div className="space-y-1">
                    <dt className="font-medium text-foreground">電話番号</dt>
                    <dd className="text-muted-foreground">{gym.phone ?? "未登録"}</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>

            <GymMapPlaceholder address={gym.address ?? undefined} />
          </div>
        </div>
      </div>
    </div>
  );
}
