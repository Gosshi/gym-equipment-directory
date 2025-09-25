import Link from "next/link";
import type { KeyboardEvent, MouseEvent } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
          "flex h-full flex-col overflow-hidden rounded-2xl border border-border/70 bg-background/95 shadow-sm transition",
          "group-hover:border-primary group-hover:shadow-md",
          isSelected ? "border-primary ring-2 ring-primary/40" : undefined,
        )}
      >
        <div className="flex h-44 items-center justify-center bg-muted text-sm text-muted-foreground">
          {gym.thumbnailUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              alt={gym.name}
              className="h-full w-full object-cover transition group-hover:scale-[1.03]"
              decoding="async"
              loading="lazy"
              src={gym.thumbnailUrl}
            />
          ) : (
            <span className="text-xs">画像なし</span>
          )}
        </div>
        <CardHeader className="space-y-1.5">
          <CardTitle className="text-lg font-semibold leading-tight tracking-tight group-hover:text-primary sm:text-xl">
            {gym.name}
          </CardTitle>
          <CardDescription className="text-sm text-muted-foreground" data-testid="gym-address">
            {addressLabel}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-3">
          {displayItems.length > 0 ? (
            <div className="flex flex-wrap gap-2" data-testid="gym-equipments">
              {displayItems.map(equipment => (
                <span
                  key={equipment}
                  className="rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground"
                >
                  {equipment}
                </span>
              ))}
              {remainingCount > 0 ? (
                <span className="rounded-full border border-dashed border-secondary px-2.5 py-1 text-xs text-muted-foreground">
                  +{remainingCount}
                </span>
              ) : null}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">設備情報はまだ登録されていません。</p>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
