"use client";

import Link from "next/link";
import { ExternalLink, Heart, MapPin } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface GymDetailHeaderProps {
  name: string;
  locationLabel?: string;
  address?: string;
  website?: string | null;
  onToggleFavorite: () => void;
  favoriteActive: boolean;
  favoriteDisabled?: boolean;
  favoritePending?: boolean;
  favoriteError?: string | null;
}

export function GymDetailHeader({
  name,
  locationLabel,
  address,
  website,
  onToggleFavorite,
  favoriteActive,
  favoriteDisabled = false,
  favoritePending = false,
  favoriteError,
}: GymDetailHeaderProps) {
  const favoriteLabel = favoriteActive ? "お気に入り済み" : "お気に入りに追加";
  const disabled = favoriteDisabled || favoritePending;

  return (
    <header className="flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-start md:justify-between">
      <div className="space-y-3">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl">{name}</h1>
          {locationLabel ? (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <MapPin aria-hidden className="h-4 w-4" />
              <span>{locationLabel}</span>
            </p>
          ) : null}
        </div>
        {address ? <p className="text-sm text-muted-foreground">{address}</p> : null}
      </div>
      <div className="flex flex-col items-start gap-3 md:items-end">
        <div className="flex flex-wrap items-center gap-2">
          {website ? (
            <Button asChild size="sm">
              <Link href={website} rel="noreferrer noopener" target="_blank">
                <ExternalLink aria-hidden className="h-4 w-4" />
                <span className="ml-2">公式サイトへ</span>
              </Link>
            </Button>
          ) : null}
          <Button
            aria-pressed={favoriteActive}
            aria-label={favoriteLabel}
            className={cn(
              "flex items-center gap-2",
              favoriteActive ? "bg-rose-500 text-white hover:bg-rose-500/90" : undefined,
            )}
            disabled={disabled}
            onClick={onToggleFavorite}
            size="sm"
            type="button"
            variant={favoriteActive ? "default" : "outline"}
          >
            <Heart
              aria-hidden
              className="h-4 w-4"
              fill={favoriteActive ? "currentColor" : "none"}
              strokeWidth={favoriteActive ? 0 : 2}
            />
            <span>{favoriteLabel}</span>
          </Button>
        </div>
        <div aria-live="polite" className="min-h-[1.25rem] text-xs text-muted-foreground">
          {favoritePending ? <span>更新中...</span> : null}
          {!favoritePending && favoriteError ? (
            <span className="text-destructive">{favoriteError}</span>
          ) : null}
        </div>
      </div>
    </header>
  );
}
