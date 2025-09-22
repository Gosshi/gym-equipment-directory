"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/apiClient";
import { cn } from "@/lib/utils";
import { searchGyms } from "@/services/gyms";
import type { GymSummary } from "@/types/gym";

const DEFAULT_PER_PAGE = 12;

type FormState = {
  q: string;
  prefecture: string;
  city: string;
};

type FetchMeta = {
  total: number;
  hasNext: boolean;
};

const parsePageParam = (value: string | null): number => {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
};

const formatSlug = (value: string) =>
  value
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");

const formatDate = (value: string | null | undefined) => {
  if (!value) {
    return undefined;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString();
};

const buildUrl = (pathname: string, params: URLSearchParams) => {
  const queryString = params.toString();
  return queryString ? `${pathname}?${queryString}` : pathname;
};

const GymsSkeleton = () => (
  <div
    aria-hidden
    className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
    role="presentation"
  >
    {Array.from({ length: 6 }).map((_, index) => (
      <Card key={index} className="overflow-hidden">
        <Skeleton className="h-40 w-full" />
        <CardContent className="space-y-3">
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <div className="flex gap-2">
            <Skeleton className="h-6 w-16 rounded-full" />
            <Skeleton className="h-6 w-16 rounded-full" />
            <Skeleton className="h-6 w-16 rounded-full" />
          </div>
        </CardContent>
      </Card>
    ))}
  </div>
);

const GymCard = ({ gym }: { gym: GymSummary }) => (
  <Card className="flex h-full flex-col overflow-hidden">
    <div className="flex h-40 items-center justify-center bg-muted text-sm text-muted-foreground">
      {gym.thumbnailUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          alt={gym.name}
          className="h-full w-full object-cover"
          src={gym.thumbnailUrl}
        />
      ) : (
        <span>画像なし</span>
      )}
    </div>
    <CardHeader className="space-y-2">
      <CardTitle className="text-xl">{gym.name}</CardTitle>
      <CardDescription className="text-sm text-muted-foreground">
        {gym.prefecture ? formatSlug(gym.prefecture) : "エリア未設定"}
        {gym.city ? ` / ${formatSlug(gym.city)}` : null}
      </CardDescription>
    </CardHeader>
    <CardContent className="flex flex-1 flex-col gap-4">
      {gym.address ? <p className="text-sm text-muted-foreground">{gym.address}</p> : null}
      {gym.equipments && gym.equipments.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {gym.equipments.slice(0, 6).map((equipment) => (
            <span
              key={equipment}
              className="rounded-full bg-secondary px-2 py-1 text-xs text-secondary-foreground"
            >
              {equipment}
            </span>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">設備情報は後ほど追加予定です。</p>
      )}
      <div className="mt-auto flex flex-col gap-1 text-xs text-muted-foreground">
        {gym.score != null ? <span>設備スコア: {gym.score.toFixed(1)}</span> : null}
        {formatDate(gym.lastVerifiedAt) ? (
          <span>最終更新: {formatDate(gym.lastVerifiedAt)}</span>
        ) : null}
      </div>
    </CardContent>
  </Card>
);

const NearbyPlaceholder = () => (
  <Card aria-live="polite" className="sticky top-24">
    <CardHeader>
      <CardTitle>近くのジム</CardTitle>
      <CardDescription>
        現在地から近いジムを探す UI は次のステップで実装予定です。
      </CardDescription>
    </CardHeader>
    <CardContent className="space-y-3">
      <p className="text-sm text-muted-foreground">
        位置情報の利用許可後に、距離順でジムを表示できるように準備を進めています。
      </p>
      <Button className="w-full" disabled type="button" variant="secondary">
        近くのジムを探す（準備中）
      </Button>
    </CardContent>
  </Card>
);

const PaginationControls = ({
  page,
  hasNext,
  isLoading,
  onChange,
}: {
  page: number;
  hasNext: boolean;
  isLoading: boolean;
  onChange: (nextPage: number) => void;
}) => (
  <div className="flex flex-col items-center gap-3 border-t pt-6">
    <div className="flex items-center gap-2">
      <Button
        disabled={isLoading || page <= 1}
        onClick={() => onChange(page - 1)}
        type="button"
        variant="outline"
      >
        前へ
      </Button>
      <span className="text-sm text-muted-foreground">ページ {page}</span>
      <Button
        disabled={isLoading || !hasNext}
        onClick={() => onChange(page + 1)}
        type="button"
      >
        次へ
      </Button>
    </div>
  </div>
);

const SearchForm = ({
  value,
  isSubmitting,
  onChange,
  onSubmit,
}: {
  value: FormState;
  isSubmitting: boolean;
  onChange: (value: FormState) => void;
  onSubmit: () => void;
}) => (
  <form
    className="grid gap-4 rounded-lg border bg-card p-6 shadow-sm"
    onSubmit={(event) => {
      event.preventDefault();
      onSubmit();
    }}
  >
    <div className="grid gap-2">
      <label className="text-sm font-medium" htmlFor="gym-search-q">
        キーワード
      </label>
      <input
        autoComplete="off"
        className="h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        id="gym-search-q"
        name="q"
        onChange={(event) => onChange({ ...value, q: event.target.value })}
        placeholder="設備やジム名を入力"
        value={value.q}
      />
    </div>
    <div className="grid gap-2 sm:grid-cols-2 sm:gap-4">
      <div className="grid gap-2">
        <label className="text-sm font-medium" htmlFor="gym-search-prefecture">
          都道府県スラッグ
        </label>
        <input
          autoComplete="off"
          className="h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          id="gym-search-prefecture"
          name="prefecture"
          onChange={(event) =>
            onChange({ ...value, prefecture: event.target.value.trim().toLowerCase() })
          }
          placeholder="例: tokyo"
          value={value.prefecture}
        />
      </div>
      <div className="grid gap-2">
        <label className="text-sm font-medium" htmlFor="gym-search-city">
          市区町村スラッグ
        </label>
        <input
          autoComplete="off"
          className="h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          id="gym-search-city"
          name="city"
          onChange={(event) => onChange({ ...value, city: event.target.value.trim().toLowerCase() })}
          placeholder="例: shinjuku"
          value={value.city}
        />
      </div>
    </div>
    <div className="flex justify-end gap-3">
      <Button
        className="w-full sm:w-auto"
        disabled={isSubmitting}
        type="submit"
      >
        検索
      </Button>
    </div>
  </form>
);

export function GymsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const queryState = useMemo(() => {
    const params = new URLSearchParams(searchParams.toString());
    const q = params.get("q") ?? "";
    const prefecture = params.get("prefecture") ?? "";
    const city = params.get("city") ?? "";
    const page = parsePageParam(params.get("page"));
    return { q, prefecture, city, page };
  }, [searchParams]);

  const [formState, setFormState] = useState<FormState>({
    q: queryState.q,
    prefecture: queryState.prefecture,
    city: queryState.city,
  });

  useEffect(() => {
    setFormState({ q: queryState.q, prefecture: queryState.prefecture, city: queryState.city });
  }, [queryState.q, queryState.prefecture, queryState.city]);

  const [items, setItems] = useState<GymSummary[]>([]);
  const [meta, setMeta] = useState<FetchMeta>({ total: 0, hasNext: false });
  const [isLoading, setIsLoading] = useState(false);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshCount, setRefreshCount] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    setIsLoading(true);
    setError(null);

    searchGyms(
      {
        q: queryState.q || undefined,
        prefecture: queryState.prefecture || undefined,
        city: queryState.city || undefined,
        page: queryState.page,
        perPage: DEFAULT_PER_PAGE,
      },
      { signal: controller.signal },
    )
      .then((response) => {
        if (cancelled) {
          return;
        }
        setItems(response.items);
        setMeta({
          total: response.meta.total,
          hasNext: response.meta.hasNext,
        });
        setHasLoadedOnce(true);
      })
      .catch((err) => {
        if (cancelled) {
          return;
        }
        if (
          (err instanceof DOMException && err.name === "AbortError") ||
          (err instanceof Error && err.name === "AbortError")
        ) {
          return;
        }
        if (err instanceof ApiError) {
          setError(err.message || "ジムの取得に失敗しました");
        } else if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
        } else {
          setError("ジムの取得に失敗しました");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [queryState.q, queryState.prefecture, queryState.city, queryState.page, refreshCount]);

  const updateQuery = (updater: (current: URLSearchParams) => void) => {
    const next = new URLSearchParams(searchParams.toString());
    updater(next);
    const url = buildUrl(pathname, next);
    router.push(url, { scroll: false });
  };

  const handleSubmit = () => {
    updateQuery((params) => {
      if (formState.q.trim()) {
        params.set("q", formState.q.trim());
      } else {
        params.delete("q");
      }

      if (formState.prefecture.trim()) {
        params.set("prefecture", formState.prefecture.trim());
      } else {
        params.delete("prefecture");
      }

      if (formState.city.trim()) {
        params.set("city", formState.city.trim());
      } else {
        params.delete("city");
      }

      params.delete("page");
    });
  };

  const handleChangePage = (nextPage: number) => {
    updateQuery((params) => {
      if (nextPage <= 1) {
        params.delete("page");
      } else {
        params.set("page", String(nextPage));
      }
    });
  };

  const handleRetry = () => setRefreshCount((count) => count + 1);

  const showSkeleton = isLoading && !hasLoadedOnce;

  return (
    <div className="flex min-h-screen w-full flex-col gap-8 px-4 py-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-wide text-muted-foreground">Gym Directory</p>
          <h1 className="text-3xl font-bold sm:text-4xl">ジム一覧</h1>
          <p className="text-sm text-muted-foreground">
            都道府県や市区町村で絞り込み、設備情報を確認できます。URL を共有すると検索条件も再現されます。
          </p>
        </header>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-6">
            <SearchForm
              isSubmitting={isLoading}
              onChange={setFormState}
              onSubmit={handleSubmit}
              value={formState}
            />
            <section
              aria-busy={isLoading}
              aria-live="polite"
              className="rounded-lg border bg-background p-6 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-3 pb-4">
                <div>
                  <h2 className="text-xl font-semibold">検索結果</h2>
                  <p className="text-sm text-muted-foreground">
                    {meta.total} 件のジムが見つかりました。
                  </p>
                </div>
              </div>
              {error ? (
                <div className="flex flex-col items-center gap-4 rounded-md border border-destructive/40 bg-destructive/10 p-6 text-center">
                  <p className="text-sm text-destructive">{error}</p>
                  <Button onClick={handleRetry} type="button" variant="outline">
                    もう一度試す
                  </Button>
                </div>
              ) : showSkeleton ? (
                <GymsSkeleton />
              ) : items.length === 0 ? (
                <p className="rounded-md bg-muted/40 p-4 text-center text-sm text-muted-foreground">
                  条件に一致するジムが見つかりませんでした。
                </p>
              ) : (
                <div className={cn("grid gap-4", "sm:grid-cols-2", "xl:grid-cols-3")}>
                  {items.map((gym) => (
                    <GymCard key={gym.id} gym={gym} />
                  ))}
                </div>
              )}
              {!error && (items.length > 0 || queryState.page > 1 || meta.hasNext) ? (
                <PaginationControls
                  hasNext={meta.hasNext}
                  isLoading={isLoading}
                  onChange={handleChangePage}
                  page={queryState.page}
                />
              ) : null}
            </section>
          </div>
          <aside className="space-y-6">
            <NearbyPlaceholder />
          </aside>
        </div>
      </div>
    </div>
  );
}
