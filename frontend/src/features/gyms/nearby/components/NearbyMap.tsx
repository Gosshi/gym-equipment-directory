"use client";

import { useEffect, useMemo, useRef } from "react";
import maplibregl from "maplibre-gl";
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

const MAP_STYLE_URL = "https://demotiles.maplibre.org/style.json";
const DEFAULT_ZOOM = 13;
const MARKER_BASE_CLASS =
  "nearby-marker flex h-9 w-9 items-center justify-center rounded-full border border-white bg-primary text-xs font-semibold text-primary-foreground shadow-lg transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-ring";
const MARKER_HIGHLIGHT_CLASSES = "ring-4 ring-offset-2 ring-primary scale-110";

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

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE_URL,
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
  }, [center.lat, center.lng, onCenterChange, zoom]);

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
      element.textContent = gym.name.charAt(0).toUpperCase();
      element.title = gym.name;

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
