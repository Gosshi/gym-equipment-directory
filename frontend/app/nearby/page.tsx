"use client";

import { useEffect, useMemo, useState, useCallback } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getNearbyGyms, type NearbyResponse } from "@/lib/api";
import FavoriteButton from "@/components/FavoriteButton";

type Coords = { lat: number; lng: number } | null;

function formatDistanceKm(d?: number) {
  if (d === undefined || d === null) return "-";
  return `${d.toFixed(2)} km`;
}

function useQueryNumbers() {
  const sp = useSearchParams();
  return useMemo(() => {
    const radius_km = sp.get("radius_km") ? Number(sp.get("radius_km")) : 5;
    const per_page = sp.get("per_page") ? Number(sp.get("per_page")) : 10;
    return { radius_km, per_page };
  }, [sp]);
}

function useGeolocation(timeoutMs = 8000) {
  const [coords, setCoords] = useState<Coords>(null);
  const [error, setError] = useState<string | null>(null);
  const [requested, setRequested] = useState(false);

  useEffect(() => {
    if (requested) return; // only once on mount
    setRequested(true);
    if (!("geolocation" in navigator)) {
      setError("このブラウザでは位置情報が利用できません。");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      pos => {
        setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      },
      err => {
        if (err.code === err.PERMISSION_DENIED) setError("位置情報の利用が拒否されました。");
        else if (err.code === err.TIMEOUT) setError("位置情報の取得がタイムアウトしました。");
        else setError("位置情報の取得に失敗しました。");
      },
      { enableHighAccuracy: false, timeout: timeoutMs, maximumAge: 0 },
    );
  }, [requested, timeoutMs]);

  return { coords, error } as const;
}

export default function NearbyPage() {
  const { radius_km, per_page } = useQueryNumbers();
  const { coords, error: geoError } = useGeolocation(8000);

  const [pageToken, setPageToken] = useState<string | null>(null);

  // Reset pagination when base params change
  useEffect(() => {
    setPageToken(null);
  }, [radius_km, per_page, coords?.lat, coords?.lng]);

  const enabled = !!coords && Number.isFinite(coords.lat) && Number.isFinite(coords.lng);

  const { data, isLoading, isError, error } = useQuery<NearbyResponse>({
    queryKey: ["nearby", coords?.lat ?? null, coords?.lng ?? null, radius_km, per_page, pageToken],
    queryFn: () =>
      getNearbyGyms({
        lat: coords!.lat,
        lng: coords!.lng,
        radius_km,
        per_page,
        page_token: pageToken,
      }),
    enabled,
  });

  const gyms = (data?.items as any[]) ?? ((data as any)?.gyms as any[]) ?? [];
  const hasNext = Boolean(data?.has_next);
  const nextToken = (data?.page_token as string | null) ?? null;

  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();

  const updateQuery = useCallback(
    (patch: Record<string, string | number | undefined>) => {
      const q = new URLSearchParams(sp.toString());
      Object.entries(patch).forEach(([k, v]) => {
        if (v === undefined || v === "") q.delete(k);
        else q.set(k, String(v));
      });
      router.replace(`${pathname}?${q.toString()}`);
    },
    [pathname, router, sp],
  );

  const [form, setForm] = useState({
    radius_km: String(radius_km),
    per_page: String(per_page),
  });
  useEffect(() => {
    setForm({ radius_km: String(radius_km), per_page: String(per_page) });
  }, [radius_km, per_page]);

  const submitParams = (e: React.FormEvent) => {
    e.preventDefault();
    const r = Number(form.radius_km) || 5;
    const p = Number(form.per_page) || 10;
    setPageToken(null);
    updateQuery({ radius_km: r, per_page: p });
  };

  // Fallback address inputs for /search redirect
  const [fallback, setFallback] = useState({ pref: "", city: "" });
  const searchHref = useMemo(() => {
    const q = new URLSearchParams();
    if (fallback.pref) q.set("pref", fallback.pref);
    if (fallback.city) q.set("city", fallback.city);
    return `/search?${q.toString()}`;
  }, [fallback.city, fallback.pref]);

  return (
    <div className="stack">
      <h1>近くのジム</h1>

      <form className="card row" onSubmit={submitParams} style={{ alignItems: "flex-end" }}>
        <label>
          Radius (km):
          <input
            type="number"
            min={1}
            step={1}
            value={form.radius_km}
            onChange={e => setForm(s => ({ ...s, radius_km: e.target.value }))}
          />
        </label>
        <label>
          Per page:
          <select
            value={form.per_page}
            onChange={e => setForm(s => ({ ...s, per_page: e.target.value }))}
          >
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
          </select>
        </label>
        <button className="btn" type="submit">
          更新
        </button>
        <button className="btn secondary" type="button" onClick={() => setPageToken(null)}>
          Reset page
        </button>
      </form>

      {!coords && !geoError && <div className="card">現在地を取得中…</div>}

      {geoError && (
        <div className="card stack">
          <div>{geoError}</div>
          <div className="muted">住所で検索に切り替えできます。</div>
          <div className="row">
            <label>
              Pref:
              <input
                type="text"
                value={fallback.pref}
                onChange={e => setFallback(s => ({ ...s, pref: e.target.value }))}
                placeholder="例: 東京都"
              />
            </label>
            <label>
              City:
              <input
                type="text"
                value={fallback.city}
                onChange={e => setFallback(s => ({ ...s, city: e.target.value }))}
                placeholder="例: 渋谷区"
              />
            </label>
            <Link className="btn" href={searchHref}>
              住所で検索へ
            </Link>
          </div>
        </div>
      )}

      {coords && (
        <div className="muted">
          座標: {coords.lat.toFixed(5)}, {coords.lng.toFixed(5)} / 半径 {radius_km} km
        </div>
      )}

      {coords && (
        <div className="stack">
          {isLoading && <div className="card">Loading nearby gyms…</div>}
          {isError && <div className="card">Error: {String(error)}</div>}
          {!isLoading && !isError && gyms.length === 0 && <div className="card">該当なし</div>}

          {!isLoading && !isError && gyms.length > 0 && (
            <div className="stack">
              {gyms.map((g: any) => (
                <div key={g.slug ?? g.id} className="card stack">
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <div>
                      <h3 style={{ marginBottom: 4 }}>
                        <Link href={`/gyms/${encodeURIComponent(g.slug ?? g.id ?? "")}`}>
                          {g.name ?? g.slug}
                        </Link>
                      </h3>
                      <div className="muted">{(g.pref ?? "") + (g.city ? ` ${g.city}` : "")}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div>{formatDistanceKm(g.distance_km)}</div>
                      {g.last_verified_at && (
                        <div className="muted" style={{ fontSize: "0.9rem" }}>
                          最終確認: {new Date(g.last_verified_at).toLocaleDateString("ja-JP")}
                        </div>
                      )}
                      {typeof g.id === "number" && (
                        <div style={{ marginTop: 8 }}>
                          <FavoriteButton gymId={g.id} gymSlug={g.slug} compact />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              <div className="row" style={{ justifyContent: "space-between" }}>
                <div />
                <div className="row">
                  {hasNext && nextToken && (
                    <button className="btn" onClick={() => setPageToken(nextToken)}>
                      次のページ
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
