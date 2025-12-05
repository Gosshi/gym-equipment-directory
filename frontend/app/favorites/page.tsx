"use client";

import { useFavorites } from "@/hooks/useFavorites";
import { GymCard } from "@/components/gyms/GymCard";
import Link from "next/link";
import { Loader2 } from "lucide-react";

export default function FavoritesPage() {
  const { favorites, isLoading } = useFavorites();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="animate-spin text-gray-400" size={32} />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">お気に入り一覧</h1>

      {favorites.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center text-gray-500">
          <p className="mb-4 text-lg">まだお気に入りがありません</p>
          <Link href="/gyms/search" className="text-blue-600 hover:underline">
            ジムを探す
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {favorites.map(fav => (
            <GymCard
              key={fav.gym_id}
              gym={{
                id: fav.gym_id,
                slug: fav.slug,
                name: fav.name,
                prefecture: fav.pref ?? "",
                city: fav.city ?? "",
                address: undefined, // Favorites list might not have full address
                thumbnailUrl: null,
                equipments: undefined,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
