import Link from "next/link";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { GymSummary } from "@/types/gym";

export interface GymCardProps {
  gym: GymSummary;
  className?: string;
}

export function GymCard({ gym, className }: GymCardProps) {
  return (
    <Link
      className={cn(
        "group block focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      href={`/gyms/${gym.slug}`}
    >
      <Card className="flex h-full flex-col overflow-hidden rounded-2xl border-border/70 transition group-hover:border-primary">
        <div className="flex h-44 items-center justify-center bg-muted text-sm text-muted-foreground">
          {gym.thumbnailUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              alt={gym.name}
              className="h-full w-full object-cover transition group-hover:scale-[1.03]"
              src={gym.thumbnailUrl}
            />
          ) : (
            <span>画像なし</span>
          )}
        </div>
        <CardHeader className="space-y-2">
          <CardTitle className="text-lg font-semibold leading-snug group-hover:text-primary sm:text-xl">
            {gym.name}
          </CardTitle>
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
                  className="rounded-full bg-secondary px-2.5 py-1 text-xs text-secondary-foreground"
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
}
