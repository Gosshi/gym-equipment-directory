import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { GymSearchMeta, GymSummary } from "@/types/gym";

const PAGE_SIZE_OPTIONS = [20, 40, 60];

type GymListProps = {
  gyms: GymSummary[];
  meta: GymSearchMeta;
  page: number;
  limit: number;
  isLoading: boolean;
  isInitialLoading: boolean;
  error: string | null;
  onRetry: () => void;
  onPageChange: (page: number) => void;
  onLimitChange: (limit: number) => void;
};

type PaginationControlsProps = {
  page: number;
  hasNext: boolean;
  isLoading: boolean;
  onChange: (page: number) => void;
};

const PaginationControls = ({ page, hasNext, isLoading, onChange }: PaginationControlsProps) => (
  <nav aria-label="ページネーション" className="mt-8 flex justify-center">
    <div className="flex items-center gap-3">
      <Button
        aria-label="前のページ"
        disabled={isLoading || page <= 1}
        onClick={() => onChange(page - 1)}
        type="button"
        variant="outline"
      >
        前へ
      </Button>
      <span className="text-sm text-muted-foreground">ページ {page}</span>
      <Button
        aria-label="次のページ"
        disabled={isLoading || !hasNext}
        onClick={() => onChange(page + 1)}
        type="button"
      >
        次へ
      </Button>
    </div>
  </nav>
);

const GymCard = ({ gym }: { gym: GymSummary }) => (
  <Link
    className="group block focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    href={`/gyms/${gym.slug}`}
  >
    <Card className="flex h-full flex-col overflow-hidden transition group-hover:border-primary">
      <div className="flex h-40 items-center justify-center bg-muted text-sm text-muted-foreground">
        {gym.thumbnailUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            alt={gym.name}
            className="h-full w-full object-cover transition group-hover:scale-[1.02]"
            src={gym.thumbnailUrl}
          />
        ) : (
          <span>画像なし</span>
        )}
      </div>
      <CardHeader className="space-y-2">
        <CardTitle className="text-xl group-hover:text-primary">{gym.name}</CardTitle>
        <CardDescription className="text-sm text-muted-foreground">
          {gym.prefecture ? gym.prefecture : "エリア未設定"}
          {gym.city ? ` / ${gym.city}` : null}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4">
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
          <p className="text-sm text-muted-foreground">設備情報はまだ登録されていません。</p>
        )}
      </CardContent>
    </Card>
  </Link>
);

const GymsSkeleton = () => (
  <div aria-hidden className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" role="presentation">
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

export function GymList({
  gyms,
  meta,
  page,
  limit,
  isLoading,
  isInitialLoading,
  error,
  onRetry,
  onPageChange,
  onLimitChange,
}: GymListProps) {
  const showSkeleton = isInitialLoading;
  const showEmpty = !error && !showSkeleton && gyms.length === 0;
  const totalPages = Math.max(1, Math.ceil((meta.total || 0) / Math.max(limit, 1)));
  const start = meta.total === 0 ? 0 : (page - 1) * limit + 1;
  const end = Math.min(page * limit, meta.total);

  return (
    <section
      aria-busy={isLoading}
      aria-live="polite"
      className="rounded-lg border bg-background p-6 shadow-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4">
        <div>
          <h2 className="text-xl font-semibold">検索結果</h2>
          <p className="text-sm text-muted-foreground">
            {meta.total} 件のジムが見つかりました。
            {totalPages > 1 ? `（全 ${totalPages} ページ）` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-muted-foreground" htmlFor="gym-search-limit">
            表示件数
          </label>
          <select
            className={cn(
              "h-9 rounded-md border border-input bg-background px-2 text-sm shadow-sm",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            )}
            id="gym-search-limit"
            onChange={(event) => onLimitChange(Number.parseInt(event.target.value, 10))}
            value={limit}
          >
            {PAGE_SIZE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option} 件
              </option>
            ))}
          </select>
        </div>
      </div>

      {error ? (
        <div
          className={cn(
            "flex flex-col items-center gap-4 rounded-md",
            "border border-destructive/40 bg-destructive/10 p-6 text-center",
          )}
        >
          <p className="text-sm text-destructive">{error}</p>
          <Button onClick={onRetry} type="button" variant="outline">
            もう一度試す
          </Button>
        </div>
      ) : showSkeleton ? (
        <GymsSkeleton />
      ) : showEmpty ? (
        <p className="rounded-md bg-muted/40 p-4 text-center text-sm text-muted-foreground">
          条件に一致するジムが見つかりませんでした。
        </p>
      ) : (
        <div className={cn("grid gap-4", "sm:grid-cols-2", "xl:grid-cols-3")}> 
          {gyms.map((gym) => (
            <GymCard key={gym.id} gym={gym} />
          ))}
        </div>
      )}

      {!error && !showEmpty ? (
        <div className="mt-4 flex flex-col gap-3 text-sm text-muted-foreground">
          <span>
            {meta.total} 件中 {start}-{end} 件を表示
          </span>
        </div>
      ) : null}

      {!error && (gyms.length > 0 || page > 1 || meta.hasNext) ? (
        <PaginationControls hasNext={meta.hasNext} isLoading={isLoading} onChange={onPageChange} page={page} />
      ) : null}
    </section>
  );
}
