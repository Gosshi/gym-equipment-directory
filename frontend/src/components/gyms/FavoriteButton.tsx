import { useFavorites } from "@/hooks/useFavorites";
import { cn } from "@/lib/utils";
import { Heart } from "lucide-react";

type Props = {
  gymId: number;
  className?: string;
  size?: number;
};

export function FavoriteButton({ gymId, className, size = 24 }: Props) {
  const { isFavorite, addFavorite, removeFavorite } = useFavorites();
  const active = isFavorite(gymId);

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (active) {
      removeFavorite(gymId);
    } else {
      addFavorite(gymId);
    }
  };

  return (
    <button
      onClick={handleClick}
      className={cn(
        "transition-colors hover:scale-110 active:scale-95",
        active ? "text-red-500 fill-red-500" : "text-gray-400 hover:text-red-400",
        className,
      )}
      aria-label={active ? "お気に入りから削除" : "お気に入りに追加"}
    >
      <Heart size={size} fill={active ? "currentColor" : "none"} />
    </button>
  );
}
