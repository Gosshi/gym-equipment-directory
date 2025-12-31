import Link from "next/link";
import type { KeyboardEvent, MouseEvent } from "react";

import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FavoriteButton } from "@/components/gyms/FavoriteButton";
import {
  getFacilityCategoryColorClass,
  getFacilityCategoryLabel,
  normalizeFacilityCategories,
} from "@/lib/facilityCategories";
import { cn } from "@/lib/utils";
import type { GymSummary } from "@/types/gym";

export interface GymCardProps {
  gym: GymSummary;
  className?: string;
  prefetch?: boolean;
  onSelect?: (slug: string) => void;
  isSelected?: boolean;
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
  const primaryAddress = gym.address?.trim() ?? "";

  const fallbackAddress = [gym.prefecture, gym.city].filter(Boolean).join(" ");
  const addressLabel = primaryAddress || fallbackAddress || "所在地情報なし";
  const categories = normalizeFacilityCategories(gym.categories, gym.category);
  const categoryPriority = [
    "gym",
    "pool",
    "court",
    "field",
    "hall",
    "martial_arts",
    "archery",
    "facility",
  ];
  const prioritizedCategories = [...categories].sort((a, b) => {
    const indexA = categoryPriority.indexOf(a);
    const indexB = categoryPriority.indexOf(b);
    const rankA = indexA === -1 ? categoryPriority.length : indexA;
    const rankB = indexB === -1 ? categoryPriority.length : indexB;
    return rankA - rankB;
  });

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
          <div className="absolute right-2 top-2 z-10 flex items-center gap-2">
            <FavoriteButton gymId={gym.id} />
          </div>
          <div className="aspect-[16/9] w-full" aria-hidden />
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
        <CardHeader className="space-y-3 px-6 pb-6 pt-5">
          <CardTitle
            className="text-lg font-semibold leading-tight tracking-tight group-hover:text-primary sm:text-xl"
            role="heading"
            aria-level={3}
          >
            {gym.name}
          </CardTitle>
          <div className="flex flex-wrap gap-2" data-testid="gym-categories">
            {prioritizedCategories.map(category => (
              <span
                key={category}
                className={cn(
                  "rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
                  "text-white shadow-sm",
                  getFacilityCategoryColorClass(category),
                )}
              >
                {getFacilityCategoryLabel(category)}
              </span>
            ))}
          </div>
          {gym.tags && gym.tags.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {gym.tags.map(tag => (
                <span
                  key={tag}
                  className={cn(
                    "inline-flex items-center rounded-md border border-border/60",
                    "bg-muted/80 px-2 py-0.5 text-[11px] font-medium text-foreground",
                  )}
                >
                  {tag}
                </span>
              ))}
            </div>
          ) : null}
          <CardDescription
            className="text-sm leading-relaxed text-muted-foreground"
            data-testid="gym-address"
          >
            {addressLabel}
          </CardDescription>
        </CardHeader>
      </Card>
    </Link>
  );
}
