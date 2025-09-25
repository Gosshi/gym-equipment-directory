"use client";

import Link from "next/link";
import { ExternalLink, Globe, Loader2, MapPin, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useGymDetail } from "@/hooks/useGymDetail";
import { cn } from "@/lib/utils";

type GymDetailPanelProps = {
  slug: string | null;
  onClose: () => void;
  className?: string;
};

type EquipmentListItem = {
  key: string;
  name: string;
  category: string | null;
};

const formatCoordinate = (value: number | null | undefined) => {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(6) : "—";
};

const ensureHttpScheme = (url: string | null | undefined): string | null => {
  if (!url) {
    return null;
  }
  if (/^https?:\/\//i.test(url)) {
    return url;
  }
  return `https://${url}`;
};

export function GymDetailPanel({ slug, onClose, className }: GymDetailPanelProps) {
  const { data, isLoading, error, reload } = useGymDetail(slug);

  if (!slug) {
    return null;
  }

  const addressLabel = data?.address?.trim()
    ? data.address.trim()
    : [data?.prefecture, data?.city].filter(Boolean).join(" ") || "住所情報が登録されていません。";

  const websiteUrl = ensureHttpScheme(data?.website ?? null);
  const equipmentItems: EquipmentListItem[] = data
    ? data.equipmentDetails && data.equipmentDetails.length > 0
      ? data.equipmentDetails
          .map((equipment, index) => {
            const trimmedName = equipment.name?.trim() ?? "";
            if (!trimmedName) {
              return null;
            }
            const category = equipment.category?.trim() ?? null;
            const key =
              equipment.id !== undefined ? String(equipment.id) : `${trimmedName}-${index}`;
            return { key, name: trimmedName, category } as EquipmentListItem;
          })
          .filter((item): item is EquipmentListItem => item !== null)
      : (data.equipments ?? [])
          .map((equipmentName, index) => {
            const trimmedName = equipmentName.trim();
            if (!trimmedName) {
              return null;
            }
            return {
              key: `${trimmedName}-${index}`,
              name: trimmedName,
              category: null,
            } as EquipmentListItem;
          })
          .filter((item): item is EquipmentListItem => item !== null)
    : [];

  return (
    <aside
      aria-live="polite"
      className={cn(
        "rounded-2xl border border-border/70 bg-card/95 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/80",
        "lg:sticky lg:top-24",
        className,
      )}
      role="complementary"
    >
      <Card className="border-0 bg-transparent shadow-none">
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div className="space-y-1.5">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
              詳細パネル
            </p>
            {isLoading ? (
              <Skeleton className="h-6 w-48" />
            ) : (
              <CardTitle className="text-lg font-semibold leading-tight">
                {data?.name ?? "ジム詳細"}
              </CardTitle>
            )}
          </div>
          <Button
            aria-label="詳細パネルを閉じる"
            className="shrink-0"
            onClick={onClose}
            size="sm"
            type="button"
            variant="ghost"
          >
            <X aria-hidden="true" className="h-4 w-4" />
            <span className="sr-only">閉じる</span>
          </Button>
        </CardHeader>
        <CardContent className="space-y-5 pb-6">
          {isLoading ? (
            <div className="flex flex-col gap-4">
              <div className="flex items-start gap-3">
                <MapPin aria-hidden="true" className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Globe aria-hidden="true" className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                </div>
              </div>
              <div className="flex items-center justify-center gap-2 rounded-lg border border-dashed border-border/70 bg-card/60 py-6 text-sm text-muted-foreground">
                <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
                詳細を読み込み中です…
              </div>
            </div>
          ) : null}

          {!isLoading && error ? (
            <div className="space-y-3 rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
              <p>{error}</p>
              <Button onClick={reload} size="sm" type="button" variant="outline">
                再試行
              </Button>
            </div>
          ) : null}

          {!isLoading && !error && data ? (
            <div className="max-h-[65vh] space-y-6 overflow-y-auto pr-1 text-sm">
              <section aria-labelledby="gym-basic-info" className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2
                    id="gym-basic-info"
                    className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground"
                  >
                    基本情報
                  </h2>
                </div>

                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <MapPin aria-hidden="true" className="mt-0.5 h-4 w-4 text-muted-foreground" />
                    <div className="space-y-1">
                      <p className="text-xs font-medium uppercase text-muted-foreground">住所</p>
                      <p className="leading-relaxed text-foreground">{addressLabel}</p>
                    </div>
                  </div>

                  <div className="rounded-lg border border-border/70 bg-background/60 p-4">
                    <p className="text-xs font-medium uppercase text-muted-foreground">座標</p>
                    <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                      <dt className="text-muted-foreground">緯度</dt>
                      <dd className="font-medium text-foreground">
                        {formatCoordinate(data.latitude)}
                      </dd>
                      <dt className="text-muted-foreground">経度</dt>
                      <dd className="font-medium text-foreground">
                        {formatCoordinate(data.longitude)}
                      </dd>
                    </dl>
                  </div>

                  <div className="flex items-start gap-3">
                    <Globe aria-hidden="true" className="mt-0.5 h-4 w-4 text-muted-foreground" />
                    <div className="space-y-1">
                      <p className="text-xs font-medium uppercase text-muted-foreground">
                        公式サイト
                      </p>
                      {websiteUrl ? (
                        <Link
                          className="inline-flex items-center gap-1 text-sm font-medium text-primary underline-offset-4 hover:underline"
                          href={websiteUrl}
                          rel="noopener noreferrer"
                          target="_blank"
                        >
                          {data.website}
                          <span aria-hidden="true" className="inline-flex">
                            <ExternalLink className="h-3.5 w-3.5" />
                          </span>
                        </Link>
                      ) : (
                        <p className="text-muted-foreground">
                          公式サイト情報が登録されていません。
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </section>

              <Separator className="border-border/60" />

              <section aria-labelledby="gym-equipments" className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2
                    id="gym-equipments"
                    className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground"
                  >
                    設備一覧
                  </h2>
                  {equipmentItems.length > 0 ? (
                    <span className="text-xs text-muted-foreground">{equipmentItems.length}件</span>
                  ) : null}
                </div>

                {equipmentItems.length > 0 ? (
                  <ul className="space-y-2">
                    {equipmentItems.map(item => (
                      <li
                        key={item.key}
                        className="flex items-center justify-between gap-3 rounded-lg border border-border/70 bg-background/60 px-3 py-2"
                      >
                        <span className="truncate text-sm font-medium text-foreground">
                          {item.name}
                        </span>
                        <Badge className="shrink-0" variant="secondary">
                          {item.category ?? "未分類"}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="rounded-md border border-dashed border-border/60 bg-muted/10 px-3 py-4 text-sm text-muted-foreground">
                    設備情報は登録されていません。
                  </p>
                )}
              </section>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </aside>
  );
}
