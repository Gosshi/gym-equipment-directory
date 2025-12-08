import Link from "next/link";
import type { KeyboardEvent, MouseEvent } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FavoriteButton } from "@/components/gyms/FavoriteButton";
import { cn } from "@/lib/utils";
import type { GymSummary } from "@/types/gym";

export interface GymCardProps {
  gym: GymSummary;
  className?: string;
  prefetch?: boolean;
  onSelect?: (slug: string) => void;
  isSelected?: boolean;
}

function getEquipmentDisplay(equipmentNames: string[] | undefined) {
  if (!equipmentNames || equipmentNames.length === 0) {
    return { displayItems: [], remainingCount: 0 };
  }

  const filtered = equipmentNames.filter(Boolean);
  const displayItems = filtered.slice(0, 5);
  const remainingCount = Math.max(filtered.length - displayItems.length, 0);

  return { displayItems, remainingCount };
}

function getPlaceholderImage(equipments: string[] | undefined): string {
  if (!equipments || equipments.length === 0) {
    return "/images/placeholders/gym-general.png";
  }

  const text = equipments.join(" ").toLowerCase();

  // Heavy/Strength keywords
  const heavyKeywords = [
    "smith",
    "rack",
    "bench",
    "dumbbell",
    "weight",
    "press",
    "スミス",
    "ラック",
    "ベンチ",
    "ダンベル",
    "ウェイト",
    "プレス",
  ];
  if (heavyKeywords.some(k => text.includes(k))) {
    return "/images/placeholders/gym-heavy.png";
  }

  // Cardio keywords
  const cardioKeywords = [
    "treadmill",
    "bike",
    "elliptical",
    "runner",
    "walker",
    "aerobic",
    "トレッドミル",
    "バイク",
    "ランニング",
    "有酸素",
  ];
  if (cardioKeywords.some(k => text.includes(k))) {
    return "/images/placeholders/gym-cardio.png";
  }

  return "/images/placeholders/gym-general.png";
}

function handleLinkKeyDown(event: KeyboardEvent<HTMLAnchorElement>) {
  if (event.defaultPrevented) {
    return;
  }

  if (event.key === " ") {
    event.preventDefault();
    event.currentTarget.click();
  }
}

function handleLinkClick(
  event: MouseEvent<HTMLAnchorElement>,
  slug: string,
  onSelect?: (slug: string) => void,
) {
  if (!onSelect) {
    return;
  }

  if (
    event.defaultPrevented ||
    event.metaKey ||
    event.ctrlKey ||
    event.altKey ||
    event.shiftKey ||
    event.button !== 0
  ) {
    return;
  }

  event.preventDefault();
  onSelect(slug);
}

export function GymCard({
  gym,
  className,
  prefetch = true,
  onSelect,
  isSelected = false,
}: GymCardProps) {
  const { displayItems, remainingCount } = getEquipmentDisplay(gym.equipments);
  const primaryAddress = gym.address?.trim() ?? "";
  const fallbackAddress = [gym.prefecture, gym.city].filter(Boolean).join(" ");
  const addressLabel = primaryAddress || fallbackAddress || "所在地情報なし";

  return (
    <Link
      aria-label={`${gym.name}の詳細を見る`}
      className={cn(
        "group block focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        "rounded-3xl",
        className,
      )}
      href={`/gyms/${gym.slug}`}
      aria-current={isSelected ? "true" : undefined}
      data-selected={isSelected ? "" : undefined}
      prefetch={prefetch}
      onClick={event => handleLinkClick(event, gym.slug, onSelect)}
      onKeyDown={handleLinkKeyDown}
      role="link"
      tabIndex={0}
    >
      <Card
        className={cn(
          "flex h-full flex-col overflow-hidden rounded-3xl border border-border/70 bg-background/95 shadow-sm transition",
          "group-hover:border-primary group-hover:shadow-lg",
          isSelected ? "border-primary ring-2 ring-primary/40" : undefined,
        )}
      >
        <div className="relative isolate overflow-hidden bg-muted">
          <div className="absolute right-2 top-2 z-10">
            <FavoriteButton gymId={gym.id} />
          </div>
          <div className="aspect-[4/3] w-full" aria-hidden />
          <div className="absolute inset-0 flex items-center justify-center bg-muted text-xs text-muted-foreground">
            {gym.thumbnailUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                alt={gym.name}
                className="h-full w-full rounded-none object-cover transition-transform duration-300 group-hover:scale-[1.04]"
                data-testid="gym-thumbnail"
                decoding="async"
                loading="lazy"
                src={gym.thumbnailUrl}
              />
            ) : (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                alt=""
                className="h-full w-full rounded-none object-cover transition-transform duration-300 group-hover:scale-[1.04]"
                data-testid="gym-thumbnail"
                decoding="async"
                loading="lazy"
                src={getPlaceholderImage(gym.equipments)}
              />
            )}
          </div>
        </div>
        <CardHeader className="space-y-2 px-6 pb-4 pt-5 sm:pb-5">
          <CardTitle
            className="text-lg font-semibold leading-tight tracking-tight group-hover:text-primary sm:text-xl"
            role="heading"
            aria-level={3}
          >
            {gym.name}
          </CardTitle>
          <CardDescription
            className="text-sm leading-relaxed text-muted-foreground"
            data-testid="gym-address"
          >
            {addressLabel}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-3 px-6 pb-6">
          {displayItems.length > 0 ? (
            <div className="flex flex-wrap gap-2" data-testid="gym-equipments">
              {displayItems.map(equipment => (
                <span
                  key={equipment}
                  className="rounded-full bg-secondary/90 px-3 py-1 text-xs font-medium leading-none text-secondary-foreground shadow-sm"
                >
                  {equipment}
                </span>
              ))}
              {remainingCount > 0 ? (
                <span className="rounded-full border border-dashed border-secondary px-3 py-1 text-xs leading-none text-muted-foreground">
                  +{remainingCount}
                </span>
              ) : null}
            </div>
          ) : (
            <p className="text-sm leading-relaxed text-muted-foreground">
              設備情報はまだ登録されていません。
            </p>
          )}

          {gym.tags && gym.tags.length > 0 ? (
            <div className="mt-auto flex flex-wrap gap-1.5 border-t border-border/50 pt-3">
              {gym.tags.map(tag => (
                <span
                  key={tag}
                  className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </Link>
  );
}
