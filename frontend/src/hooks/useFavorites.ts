import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FavoriteItem, addFavorite, listFavorites, removeFavorite } from "@/lib/api";
import { getOrCreateDeviceId } from "@/lib/device";

const FAVORITES_KEY = ["favorites"];

export function useFavorites() {
  const queryClient = useQueryClient();
  // Ensure device ID exists on client side
  const deviceId = typeof window !== "undefined" ? getOrCreateDeviceId() : "";

  const { data: favorites, isLoading } = useQuery({
    queryKey: FAVORITES_KEY,
    queryFn: () => listFavorites(deviceId),
    enabled: !!deviceId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  const addMutation = useMutation({
    mutationFn: (gymId: number) => addFavorite(deviceId, gymId),
    onMutate: async gymId => {
      await queryClient.cancelQueries({ queryKey: FAVORITES_KEY });
      const previous = queryClient.getQueryData<FavoriteItem[]>(FAVORITES_KEY);

      // Optimistic update
      queryClient.setQueryData<FavoriteItem[]>(FAVORITES_KEY, old => {
        const dummy: FavoriteItem = {
          gym_id: gymId,
          slug: "", // specific slug unknown here, but ID is enough for check
          name: "",
          pref: "",
          city: "",
        };
        return old ? [...old, dummy] : [dummy];
      });
      return { previous };
    },
    onError: (err, gymId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(FAVORITES_KEY, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: FAVORITES_KEY });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (gymId: number) => removeFavorite(deviceId, gymId),
    onMutate: async gymId => {
      await queryClient.cancelQueries({ queryKey: FAVORITES_KEY });
      const previous = queryClient.getQueryData<FavoriteItem[]>(FAVORITES_KEY);

      // Optimistic update
      queryClient.setQueryData<FavoriteItem[]>(FAVORITES_KEY, old => {
        return old ? old.filter(f => f.gym_id !== gymId) : [];
      });
      return { previous };
    },
    onError: (err, gymId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(FAVORITES_KEY, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: FAVORITES_KEY });
    },
  });

  const isFavorite = (gymId: number) => {
    return favorites?.some(f => f.gym_id === gymId) ?? false;
  };

  return {
    favorites: favorites ?? [],
    isLoading,
    isFavorite,
    addFavorite: addMutation.mutate,
    removeFavorite: removeMutation.mutate,
    isPending: addMutation.isPending || removeMutation.isPending,
  };
}
