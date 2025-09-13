"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addFavorite, listFavorites, removeFavorite } from "@/lib/api";
import { getOrCreateDeviceId } from "@/lib/device";
import { useEffect, useMemo, useState } from "react";
import { useToast } from "./Toast";

type Props = {
  gymId: number;
  gymSlug?: string;
  compact?: boolean;
};

export default function FavoriteButton({ gymId, gymSlug, compact }: Props) {
  const deviceId = useMemo(() => (typeof window !== "undefined" ? getOrCreateDeviceId() : ""), []);
  const qc = useQueryClient();
  const { notify } = useToast();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const favQuery = useQuery({
    queryKey: ["favorites", deviceId],
    queryFn: () => listFavorites(deviceId),
    enabled: Boolean(deviceId && mounted),
    staleTime: 30_000,
  });

  const isFavorite = (favQuery.data ?? []).some(it => it.gym_id === gymId);

  const addMut = useMutation({
    mutationFn: () => addFavorite(deviceId, gymId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["favorites", deviceId] });
      notify("お気に入りに追加しました");
    },
  });
  const delMut = useMutation({
    mutationFn: () => removeFavorite(deviceId, gymId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["favorites", deviceId] });
      notify("お気に入りを解除しました");
    },
  });

  const toggle = () => {
    if (isFavorite) delMut.mutate();
    else addMut.mutate();
  };

  const disabled = addMut.isPending || delMut.isPending || favQuery.isLoading;

  const label = isFavorite ? "お気に入り解除" : "お気に入り";
  const star = isFavorite ? "★" : "☆";

  return (
    <button
      className={compact ? "btn secondary" : "btn"}
      type="button"
      onClick={toggle}
      aria-pressed={isFavorite}
      aria-label={label + (gymSlug ? `: ${gymSlug}` : "")}
      disabled={disabled}
    >
      <span aria-hidden="true">{star}</span>
      {!compact && <span>{label}</span>}
    </button>
  );
}

