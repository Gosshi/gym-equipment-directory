import { cn } from "@/lib/utils";

type SearchDistanceBadgeProps = {
  distanceKm: number;
  className?: string;
};

export function SearchDistanceBadge({ distanceKm, className }: SearchDistanceBadgeProps) {
  return (
    <span
      aria-live="polite"
      className={cn(
        "inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5",
        "text-xs font-medium text-primary",
        className,
      )}
    >
      半径: 約 {distanceKm}km
    </span>
  );
}
