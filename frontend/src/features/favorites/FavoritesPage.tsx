"use client";

import { useCallback, useMemo } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/use-toast";
import { useFavorites } from "@/store/favorites";
import { useAuthGuard } from "@/routes/withAuthGuard";
import type { Favorite } from "@/types/favorite";

const formatRegion = (value?: string | null) => {
  if (!value) {
    return undefined;
  }
  return value
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

const formatLocation = (prefecture?: string, city?: string) => {
  const pref = formatRegion(prefecture);
  const locality = formatRegion(city);
  if (pref && locality) {
    return `${pref} / ${locality}`;
  }
  if (pref) {
    return pref;
  }
  if (locality) {
    return locality;
  }
  return "エリア情報未設定";
};

const formatDate = (value?: string | null) => {
  if (!value) {
    return "登録日情報はまだありません";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("ja-JP", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const FavoritesSkeleton = () => (
  <div className="flex min-h-screen flex-col gap-6 px-4 py-10">
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <div className="space-y-3">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-3/4" />
      </div>
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, index) => (
          <Card key={index} className="overflow-hidden">
            <Skeleton className="h-40 w-full" />
            <CardContent className="space-y-3 pt-6">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <div className="flex gap-2">
                <Skeleton className="h-9 w-24" />
                <Skeleton className="h-9 w-24" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  </div>
);

const FavoritesEmptyState = () => (
  <Card className="border-dashed">
    <CardHeader>
      <CardTitle className="text-xl">お気に入りがまだありません</CardTitle>
      <CardDescription>
        気になるジムを見つけたら、詳細ページからお気に入り登録してみましょう。
      </CardDescription>
    </CardHeader>
    <CardContent>
      <Button asChild type="button">
        <Link href="/gyms">ジムを探しに行く</Link>
      </Button>
    </CardContent>
  </Card>
);

const FavoritesErrorState = ({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) => (
  <Card className="border-destructive/50 bg-destructive/5">
    <CardHeader>
      <CardTitle className="text-xl text-destructive">お気に入りを取得できませんでした</CardTitle>
      <CardDescription className="text-destructive/90">{message}</CardDescription>
    </CardHeader>
    <CardContent>
      <Button onClick={onRetry} type="button" variant="outline">
        再試行する
      </Button>
    </CardContent>
  </Card>
);

const FavoriteCard = ({
  favorite,
  onRemove,
  isRemoving,
}: {
  favorite: Favorite;
  onRemove: () => void;
  isRemoving: boolean;
}) => {
  const { gym, createdAt } = favorite;
  const locationLabel = formatLocation(gym.prefecture, gym.city);
  const createdAtLabel = formatDate(createdAt);

  return (
    <Card className="overflow-hidden">
      <div className="h-40 w-full bg-muted">
        {gym.thumbnailUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            alt={`${gym.name} のサムネイル`}
            className="h-full w-full object-cover"
            src={gym.thumbnailUrl}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground">
            表示できる画像がまだありません。
          </div>
        )}
      </div>
      <CardHeader className="space-y-2">
        <CardTitle className="text-2xl">{gym.name}</CardTitle>
        <CardDescription className="text-sm text-muted-foreground">{locationLabel}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {gym.address ? <p className="text-sm text-muted-foreground">{gym.address}</p> : null}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-xs text-muted-foreground">登録日: {createdAtLabel}</div>
          <div className="flex gap-2">
            <Button asChild size="sm" type="button">
              <Link href={`/gyms/${gym.slug}`}>ジム詳細へ</Link>
            </Button>
            <Button
              disabled={isRemoving}
              onClick={onRemove}
              size="sm"
              type="button"
              variant="outline"
            >
              {isRemoving ? "更新中..." : "お気に入り解除"}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export function FavoritesPage() {
  const { favorites, status, error, removeFavorite, isPending, refresh } = useFavorites();

  const sortedFavorites = useMemo(() => {
    return [...favorites].sort((a, b) => {
      const aTime = a.createdAt ? new Date(a.createdAt).getTime() : 0;
      const bTime = b.createdAt ? new Date(b.createdAt).getTime() : 0;
      return bTime - aTime;
    });
  }, [favorites]);

  const isLoading = status === "idle" || status === "loading";
  const isSyncing = status === "syncing";

  const removeFavoriteHandler = useCallback(
    async (gymId: number, gymName: string) => {
      try {
        await removeFavorite(gymId);
        toast({
          title: "お気に入りから削除しました",
          description: `${gymName} をお気に入りから解除しました。`,
        });
      } catch (err) {
        const message =
          err instanceof Error && err.message
            ? err.message
            : "お気に入りの更新に失敗しました。もう一度お試しください。";
        toast({
          title: "お気に入りの更新に失敗しました",
          description: message,
          variant: "destructive",
        });
      }
    },
    [removeFavorite],
  );

  const handleRemove = useAuthGuard(removeFavoriteHandler);

  if (isLoading) {
    return <FavoritesSkeleton />;
  }

  return (
    <div className="flex min-h-screen flex-col gap-6 px-4 py-10">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-wide text-muted-foreground">My Favorites</p>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">お気に入り一覧</h1>
          <p className="text-sm text-muted-foreground">
            詳細ページで登録したジムのお気に入りをここで管理できます。
          </p>
        </header>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          {error ? (
            <p className="text-sm text-destructive">{error}</p>
          ) : (
            <p className="text-sm text-muted-foreground">
              {isSyncing ? "最新の情報を取得しています..." : "お気に入りは自動的に同期されます。"}
            </p>
          )}
          <Button
            disabled={isSyncing}
            onClick={() => {
              void refresh();
            }}
            size="sm"
            type="button"
            variant="outline"
          >
            再読み込み
          </Button>
        </div>

        {error && sortedFavorites.length === 0 ? (
          <FavoritesErrorState
            message={error}
            onRetry={() => {
              void refresh();
            }}
          />
        ) : null}

        {sortedFavorites.length === 0 ? (
          <FavoritesEmptyState />
        ) : (
          <div className="space-y-4">
            {sortedFavorites.map((favorite) => (
              <FavoriteCard
                key={favorite.gym.id}
                favorite={favorite}
                isRemoving={isPending(favorite.gym.id)}
                onRemove={() => {
                  void handleRemove(favorite.gym.id, favorite.gym.name);
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
