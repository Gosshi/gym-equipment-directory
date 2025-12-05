import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";

import { FavoriteButton } from "@/components/gyms/FavoriteButton";

interface GymHeaderProps {
  gymId: number;
  name: string;
  address?: string;
  locationLabel?: string;
  categories: string[];
  actions?: ReactNode;
}

export function GymHeader({
  gymId,
  name,
  address,
  locationLabel,
  categories,
  actions,
}: GymHeaderProps) {
  return (
    <header className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="space-y-3">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{name}</h1>
          <div className="space-y-1 text-sm text-muted-foreground">
            <p>{address ?? "住所情報は現在準備中です。"}</p>
            {locationLabel ? <p>{locationLabel}</p> : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-3">
          {actions}
          <FavoriteButton gymId={gymId} size={32} className="p-2" />
        </div>
      </div>
      {categories.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {categories.map(category => (
            <Badge key={category} variant="secondary">
              {category}
            </Badge>
          ))}
        </div>
      ) : null}
    </header>
  );
}
