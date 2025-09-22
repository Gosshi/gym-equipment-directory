"use client";

import { useEffect, useMemo, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { NearbyGym } from "@/types/gym";

export interface NearbyMapProps {
  center: { lat: number; lng: number };
  markers: NearbyGym[];
  hoveredId: number | null;
  onMarkerHover: (id: number | null) => void;
  onMarkerSelect: (gym: NearbyGym) => void;
  onCenterChange: (nextCenter: { lat: number; lng: number }) => void;
  zoom?: number;
}

const FALLBACK_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: [
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
      ],
      tileSize: 256,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright" rel="noopener noreferrer" target="_blank">OpenStreetMap</a> contributors',
      maxzoom: 19,
    },
  },
  layers: [
    {
      id: "osm-base",
      type: "raster",
      source: "osm",
    },
  ],
  glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
};

const resolveMapStyle = (): string | StyleSpecification => {
  const inline = process.env.NEXT_PUBLIC_MAP_STYLE_JSON?.trim();
  if (inline) {
    try {
      return JSON.parse(inline) as StyleSpecification;
    } catch (error) {
      if (process.env.NODE_ENV !== "production") {
        // eslint-disable-next-line no-console
        console.warn("Failed to parse NEXT_PUBLIC_MAP_STYLE_JSON", error);
      }
    }
  }

  const url = process.env.NEXT_PUBLIC_MAP_STYLE_URL?.trim();
  if (url) {
    return url;
  }

  return FALLBACK_STYLE;
};
const DEFAULT_ZOOM = 13;
const MARKER_BASE_CLASS =
  "nearby-marker flex h-11 w-11 items-center justify-center rounded-full border-2 border-red-400/70 bg-white/90 text-3xl text-red-500 shadow-[0_8px_18px_rgba(0,0,0,0.15)] backdrop-blur-sm transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-red-500";
const MARKER_HIGHLIGHT_CLASSES = "ring-4 ring-red-500/80 ring-offset-2 scale-110";

const logMapCenter = (payload: Record<string, unknown>) => {
  if (typeof window !== "undefined" && process.env.NODE_ENV !== "test") {
    // eslint-disable-next-line no-console
    console.debug("map_center_changed", payload);
  }
};

export function NearbyMap({
  center,
  markers,
  hoveredId,
  onMarkerHover,
  onMarkerSelect,
  onCenterChange,
  zoom = DEFAULT_ZOOM,
}: NearbyMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerMapRef = useRef(
    new Map<number, { marker: maplibregl.Marker; element: HTMLButtonElement }>(),
  );
  const suppressMoveRef = useRef(false);

  const mapStyle = useMemo(() => resolveMapStyle(), []);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: mapStyle,
      center: [center.lng, center.lat],
      zoom,
    });
    const markerStore = markerMapRef.current;

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

    map.on("moveend", () => {
      if (suppressMoveRef.current) {
        suppressMoveRef.current = false;
        return;
      }
      const next = map.getCenter();
      const payload = { lat: Number(next.lat.toFixed(6)), lng: Number(next.lng.toFixed(6)) };
      logMapCenter({ ...payload, zoom: map.getZoom() });
      onCenterChange(payload);
    });

    mapRef.current = map;

    const handleResize = () => map.resize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      markerStore.forEach(({ marker }) => marker.remove());
      markerStore.clear();
      map.remove();
      mapRef.current = null;
    };
  }, [center.lat, center.lng, mapStyle, onCenterChange, zoom]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const current = map.getCenter();
    const sameLat = Number.parseFloat(current.lat.toFixed(6)) === Number.parseFloat(center.lat.toFixed(6));
    const sameLng = Number.parseFloat(current.lng.toFixed(6)) === Number.parseFloat(center.lng.toFixed(6));
    if (sameLat && sameLng) {
      return;
    }

    suppressMoveRef.current = true;
    map.easeTo({ center: [center.lng, center.lat], duration: 600 });
  }, [center.lat, center.lng]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const nextIds = new Set(markers.map((gym) => gym.id));

    markerMapRef.current.forEach((value, key) => {
      if (!nextIds.has(key)) {
        value.marker.remove();
        markerMapRef.current.delete(key);
      }
    });

    markers.forEach((gym) => {
      const existing = markerMapRef.current.get(gym.id);
      if (existing) {
        existing.marker.setLngLat([gym.longitude, gym.latitude]);
        return;
      }

      const element = document.createElement("button");
      element.type = "button";
      element.className = MARKER_BASE_CLASS;
      element.textContent = "📍";
      element.setAttribute("aria-label", `${gym.name} の詳細を開く`);
      element.title = buildTooltip(gym);

      element.addEventListener("mouseenter", () => onMarkerHover(gym.id));
      element.addEventListener("mouseleave", () => onMarkerHover(null));
      element.addEventListener("focus", () => onMarkerHover(gym.id));
      element.addEventListener("blur", () => onMarkerHover(null));
      element.addEventListener("click", () => onMarkerSelect(gym));

      const marker = new maplibregl.Marker({ element, anchor: "bottom" })
        .setLngLat([gym.longitude, gym.latitude])
        .addTo(map);

      markerMapRef.current.set(gym.id, { marker, element });
    });
  }, [markers, onMarkerHover, onMarkerSelect]);

  const highlightClasses = useMemo(() => MARKER_HIGHLIGHT_CLASSES.split(" "), []);

  useEffect(() => {
    markerMapRef.current.forEach(({ element }, id) => {
      highlightClasses.forEach((cls) => {
        if (id === hoveredId) {
          element.classList.add(cls);
        } else {
          element.classList.remove(cls);
        }
      });
    });
  }, [hoveredId, highlightClasses]);

  return <div className="h-[420px] w-full rounded-lg border" ref={containerRef} />;
}

const buildTooltip = (gym: NearbyGym) => {
  const distance = formatDistance(gym.distanceKm);
  const area = formatArea(gym);
  return `${gym.name} / ${area} / ${distance}`;
};

const formatDistance = (distanceKm: number) => {
  if (distanceKm < 1) {
    return `${Math.round(distanceKm * 1000)}m`;
  }
  return `${distanceKm.toFixed(1)}km`;
};

const formatSlug = (value: string | null | undefined) => {
  if (!value) {
    return null;
  }
  return value
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

const formatArea = (gym: NearbyGym) => {
  const pref = formatSlug(gym.prefecture);
  const city = formatSlug(gym.city);
  const joined = [pref, city].filter(Boolean).join(" / ");
  return joined || "エリア不明";
};
