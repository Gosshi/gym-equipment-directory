"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

import type { LeafletClientMapProps } from "./LeafletClientMap";

const LeafletMap = dynamic<LeafletClientMapProps>(() => import("./LeafletClientMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-muted" />,
});

interface GymMapProps {
  name: string;
  address?: string;
  latitude?: number;
  longitude?: number;
}

type Coordinates = { lat: number; lng: number };

const hasValidCoordinate = (value?: number): value is number =>
  typeof value === "number" && Number.isFinite(value);

const NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search";

type GeocodeState =
  | { status: "idle"; coordinates: null; error: null }
  | { status: "loading"; coordinates: null; error: null }
  | { status: "success"; coordinates: Coordinates; error: null }
  | { status: "error"; coordinates: null; error: string };

const INITIAL_STATE: GeocodeState = { status: "idle", coordinates: null, error: null };

export function GymMap({ name, address, latitude, longitude }: GymMapProps) {
  const [state, setState] = useState<GeocodeState>(() => {
    if (hasValidCoordinate(latitude) && hasValidCoordinate(longitude)) {
      return {
        status: "success",
        coordinates: { lat: latitude, lng: longitude },
        error: null,
      } satisfies GeocodeState;
    }
    return INITIAL_STATE;
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const lastGeocodedAddressRef = useRef<string | null>(null);

  const sanitizedAddress = useMemo(() => {
    if (!address) {
      return undefined;
    }
    const trimmed = address.trim();
    return trimmed.length > 0 ? trimmed : undefined;
  }, [address]);

  useEffect(() => {
    if (hasValidCoordinate(latitude) && hasValidCoordinate(longitude)) {
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      lastGeocodedAddressRef.current = null;
      setState({
        status: "success",
        coordinates: { lat: latitude, lng: longitude },
        error: null,
      });
      return;
    }

    if (!sanitizedAddress) {
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      lastGeocodedAddressRef.current = null;
      setState(INITIAL_STATE);
      return;
    }

    if (state.status === "success" && lastGeocodedAddressRef.current === sanitizedAddress) {
      return;
    }

    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setState({ status: "loading", coordinates: null, error: null });

    const query = new URLSearchParams({
      q: sanitizedAddress,
      format: "jsonv2",
      limit: "1",
    });

    fetch(`${NOMINATIM_ENDPOINT}?${query.toString()}`, {
      headers: {
        Accept: "application/json",
        "Accept-Language": "ja",
      },
      signal: controller.signal,
    })
      .then(async response => {
        if (!response.ok) {
          throw new Error(`Geocoding request failed with status ${response.status}`);
        }
        const results = (await response.json()) as Array<{
          lat?: string;
          lon?: string;
        }>;
        if (!Array.isArray(results) || results.length === 0) {
          throw new Error("住所に対応する位置情報が見つかりませんでした");
        }
        const [first] = results;
        const lat = Number.parseFloat(first?.lat ?? "");
        const lng = Number.parseFloat(first?.lon ?? "");
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
          throw new Error("緯度経度の解析に失敗しました");
        }
        lastGeocodedAddressRef.current = sanitizedAddress;
        setState({
          status: "success",
          coordinates: { lat, lng },
          error: null,
        });
      })
      .catch(error => {
        if (controller.signal.aborted) {
          return;
        }
        const message =
          error instanceof Error && error.message
            ? error.message
            : "住所から位置情報を取得できませんでした";
        setState({ status: "error", coordinates: null, error: message });
      });

    return () => {
      controller.abort();
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
    };
  }, [latitude, longitude, sanitizedAddress, state.status]);

  const coordinates = state.status === "success" ? state.coordinates : null;

  const mapQuery = coordinates
    ? `${coordinates.lat},${coordinates.lng}`
    : sanitizedAddress
      ? `${sanitizedAddress}`
      : undefined;

  const mapUrl = mapQuery
    ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(mapQuery)}`
    : undefined;

  return (
    <Card>
      <CardHeader>
        <CardTitle>地図</CardTitle>
        <CardDescription>所在地の確認やルート検索にご利用ください。</CardDescription>
      </CardHeader>
      <CardContent>
        {coordinates ? (
          <div className="aspect-[4/3] overflow-hidden rounded-lg">
            <LeafletMap
              address={address ?? ""}
              lat={coordinates.lat}
              lng={coordinates.lng}
              name={name}
            />
          </div>
        ) : state.status === "loading" ? (
          <div className="flex min-h-[6rem] items-center justify-center rounded-lg border border-dashed">
            <p className="text-sm text-muted-foreground">地図情報を取得しています…</p>
          </div>
        ) : (
          <div className="flex min-h-[6rem] items-center justify-center rounded-lg border border-dashed">
            <p className="text-sm text-muted-foreground">
              地図情報なし{state.error ? `（${state.error}）` : ""}
            </p>
          </div>
        )}
      </CardContent>
      <CardFooter>
        {mapUrl ? (
          <Button asChild variant="outline">
            <Link href={mapUrl} rel="noopener noreferrer" target="_blank">
              Google Maps で開く
            </Link>
          </Button>
        ) : (
          <p className="text-sm text-muted-foreground">Google Maps へのリンクは準備中です。</p>
        )}
      </CardFooter>
    </Card>
  );
}

export default GymMap;
