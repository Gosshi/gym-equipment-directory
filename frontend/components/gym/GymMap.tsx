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
  prefecture?: string;
  city?: string;
  slug?: string;
}

type Coordinates = { lat: number; lng: number };

const hasValidCoordinate = (value?: number): value is number =>
  typeof value === "number" && Number.isFinite(value);

const sanitizeText = (value?: string | null) => {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
};

const appendJapanContext = (value: string) => {
  const trimmed = value.trim();
  if (!trimmed) {
    return trimmed;
  }
  if (/[日本]/u.test(trimmed) || trimmed.toLowerCase().includes("japan")) {
    return trimmed;
  }
  return `${trimmed} 日本`;
};

const deriveCandidateFromSlug = (slug?: string) => {
  if (!slug) {
    return undefined;
  }
  let decoded = slug;
  try {
    decoded = decodeURIComponent(slug);
  } catch (error) {
    decoded = slug;
  }
  const normalized = decoded.replace(/[_-]/g, " ");
  const withHyphenatedNumbers = normalized.replace(/(?<=\d)\s+(?=\d)/g, "-");
  const collapsed = withHyphenatedNumbers.replace(/\s+/g, " ").trim();
  if (!collapsed) {
    return undefined;
  }
  const segments = collapsed
    .split(" ")
    .filter(segment => /[^\x00-\x7F]/u.test(segment) || /\d/.test(segment));
  if (segments.length === 0) {
    return collapsed;
  }
  return segments.join(" ");
};

const NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search";

type GeocodeCandidate = { query: string; display: string };

type GeocodeState =
  | { status: "idle"; coordinates: null; error: null }
  | { status: "loading"; coordinates: null; error: null }
  | { status: "success"; coordinates: Coordinates; error: null }
  | { status: "error"; coordinates: null; error: string };

const INITIAL_STATE: GeocodeState = { status: "idle", coordinates: null, error: null };

class GeocodeError extends Error {
  constructor(
    message: string,
    readonly code: "not_found" | "invalid_response" | "request_failed",
  ) {
    super(message);
    this.name = "GeocodeError";
  }
}

async function geocode(query: string, signal: AbortSignal): Promise<Coordinates> {
  const params = new URLSearchParams({ q: query, format: "jsonv2", limit: "1" });
  const response = await fetch(`${NOMINATIM_ENDPOINT}?${params.toString()}`, {
    headers: {
      Accept: "application/json",
      "Accept-Language": "ja",
    },
    signal,
  });

  if (!response.ok) {
    throw new GeocodeError(
      `Geocoding request failed with status ${response.status}`,
      "request_failed",
    );
  }

  const results = (await response.json()) as Array<{ lat?: string; lon?: string }>;
  if (!Array.isArray(results) || results.length === 0) {
    throw new GeocodeError("住所に対応する位置情報が見つかりませんでした", "not_found");
  }

  const [first] = results;
  const lat = Number.parseFloat(first?.lat ?? "");
  const lng = Number.parseFloat(first?.lon ?? "");
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    throw new GeocodeError("緯度経度の解析に失敗しました", "invalid_response");
  }

  return { lat, lng };
}

export function GymMap({
  name,
  address,
  latitude,
  longitude,
  prefecture,
  city,
  slug,
}: GymMapProps) {
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

  const geocodeCandidates = useMemo<GeocodeCandidate[]>(() => {
    const candidates: GeocodeCandidate[] = [];
    const seen = new Set<string>();

    const pushCandidate = (value?: string | null) => {
      const sanitized = sanitizeText(value);
      if (!sanitized) {
        return;
      }
      const query = appendJapanContext(sanitized);
      if (seen.has(query)) {
        return;
      }
      seen.add(query);
      candidates.push({ query, display: sanitized });
    };

    pushCandidate(address);

    const regionParts = [sanitizeText(prefecture), sanitizeText(city)]
      .filter((part): part is string => Boolean(part))
      .join(" ");

    const nameWithRegion = [sanitizeText(name), regionParts]
      .filter((part): part is string => Boolean(part))
      .join(" ");

    if (nameWithRegion) {
      pushCandidate(nameWithRegion);
    }

    if (regionParts) {
      pushCandidate(regionParts);
    }

    pushCandidate(name);

    if (!address) {
      const slugCandidate = deriveCandidateFromSlug(slug);
      if (slugCandidate) {
        pushCandidate(slugCandidate);
      }
    }

    return candidates;
  }, [address, city, name, prefecture, slug]);

  useEffect(() => {
    if (hasValidCoordinate(latitude) && hasValidCoordinate(longitude)) {
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      setState({
        status: "success",
        coordinates: { lat: latitude, lng: longitude },
        error: null,
      });
      return;
    }

    if (geocodeCandidates.length === 0) {
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      setState(INITIAL_STATE);
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current?.abort();
    abortControllerRef.current = controller;

    setState({ status: "loading", coordinates: null, error: null });

    let isActive = true;

    (async () => {
      let lastError: string | null = null;

      for (const candidate of geocodeCandidates) {
        try {
          const coordinates = await geocode(candidate.query, controller.signal);
          if (!isActive || controller.signal.aborted) {
            return;
          }
          setState({ status: "success", coordinates, error: null });
          return;
        } catch (error) {
          if (!isActive || controller.signal.aborted) {
            return;
          }

          if (error instanceof GeocodeError) {
            if (error.code === "not_found") {
              lastError = error.message;
              continue;
            }
            lastError = error.message;
            break;
          }

          lastError =
            error instanceof Error && error.message
              ? error.message
              : "住所から位置情報を取得できませんでした";
          break;
        }
      }

      if (!isActive || controller.signal.aborted) {
        return;
      }

      setState({
        status: "error",
        coordinates: null,
        error: lastError ?? "住所に対応する位置情報が見つかりませんでした",
      });
    })()
      .catch(() => {
        // 既に setState でエラーを反映しているため、ここでは握りつぶす
      })
      .finally(() => {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
      });

    return () => {
      isActive = false;
      controller.abort();
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
    };
  }, [geocodeCandidates, latitude, longitude]);

  const coordinates = state.status === "success" ? state.coordinates : null;

  const mapQuery = coordinates
    ? `${coordinates.lat},${coordinates.lng}`
    : geocodeCandidates[0]?.query;

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
