"use client";

import { useEffect, useMemo, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { NearbyGym } from "@/types/gym";
import { useMapSelectionStore } from "@/state/mapSelection";

export interface NearbyMapProps {
  center: { lat: number; lng: number };
  markers: NearbyGym[];
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
const MARKER_HOVERED_CLASSES = Object.freeze([
  "ring-4",
  "ring-red-500/80",
  "ring-offset-2",
  "scale-110",
]);
const MARKER_SELECTED_CLASSES = Object.freeze([
  "border-red-500",
  "bg-red-500",
  "text-white",
  "scale-125",
  "shadow-lg",
]);

const logMapCenter = (payload: Record<string, unknown>) => {
  if (typeof window !== "undefined" && process.env.NODE_ENV !== "test") {
    // eslint-disable-next-line no-console
    console.debug("map_center_changed", payload);
  }
};

export function NearbyMap({
  center,
  markers,
  onMarkerSelect,
  onCenterChange,
  zoom = DEFAULT_ZOOM,
}: NearbyMapProps) {
  const hoveredId = useMapSelectionStore(state => state.hoveredId);
  const selectedId = useMapSelectionStore(state => state.selectedId);
  const lastSelectionSource = useMapSelectionStore(state => state.lastSelectionSource);
  const lastSelectionAt = useMapSelectionStore(state => state.lastSelectionAt);
  const setHovered = useMapSelectionStore(state => state.setHovered);
  const setSelected = useMapSelectionStore(state => state.setSelected);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerMapRef = useRef(
    new Map<number, { marker: maplibregl.Marker; element: HTMLButtonElement }>(),
  );
  const suppressMoveRef = useRef(false);
  const isUserDraggingRef = useRef(false);
  const pendingPanRef = useRef<number | null>(null);
  const lastMapSelectionRef = useRef<{ id: number | null; at: number | null }>({
    id: null,
    at: null,
  });

  useEffect(
    () => () => {
      if (pendingPanRef.current !== null) {
        window.clearTimeout(pendingPanRef.current);
        pendingPanRef.current = null;
      }
    },
    [],
  );

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

    const handleMoveEnd = () => {
      if (suppressMoveRef.current) {
        suppressMoveRef.current = false;
        return;
      }
      const next = map.getCenter();
      const payload = { lat: Number(next.lat.toFixed(6)), lng: Number(next.lng.toFixed(6)) };
      logMapCenter({ ...payload, zoom: map.getZoom() });
      onCenterChange(payload);
    };

    const handleDragStart = () => {
      isUserDraggingRef.current = true;
      if (pendingPanRef.current !== null) {
        window.clearTimeout(pendingPanRef.current);
        pendingPanRef.current = null;
      }
    };

    const handleDragEnd = () => {
      isUserDraggingRef.current = false;
    };

    map.on("moveend", handleMoveEnd);
    map.on("dragstart", handleDragStart);
    map.on("dragend", handleDragEnd);

    mapRef.current = map;

    const handleResize = () => map.resize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      markerStore.forEach(({ marker }) => marker.remove());
      markerStore.clear();
      if (pendingPanRef.current !== null) {
        window.clearTimeout(pendingPanRef.current);
        pendingPanRef.current = null;
      }
      isUserDraggingRef.current = false;
      map.off("moveend", handleMoveEnd);
      map.off("dragstart", handleDragStart);
      map.off("dragend", handleDragEnd);
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
    const sameLat =
      Number.parseFloat(current.lat.toFixed(6)) === Number.parseFloat(center.lat.toFixed(6));
    const sameLng =
      Number.parseFloat(current.lng.toFixed(6)) === Number.parseFloat(center.lng.toFixed(6));
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

    const nextIds = new Set(markers.map(gym => gym.id));

    markerMapRef.current.forEach((value, key) => {
      if (!nextIds.has(key)) {
        value.marker.remove();
        markerMapRef.current.delete(key);
      }
    });

    markers.forEach(gym => {
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
      element.style.zIndex = "10";
      element.dataset.gymId = String(gym.id);

      element.addEventListener("mouseenter", () => setHovered(gym.id, "map"));
      element.addEventListener("mouseleave", () => setHovered(null));
      element.addEventListener("focus", () => setHovered(gym.id, "map"));
      element.addEventListener("blur", () => setHovered(null));
      element.addEventListener("click", () => {
        setSelected(gym.id, "map");
        onMarkerSelect(gym);
      });

      const marker = new maplibregl.Marker({ element, anchor: "bottom" })
        .setLngLat([gym.longitude, gym.latitude])
        .addTo(map);

      markerMapRef.current.set(gym.id, { marker, element });
    });
  }, [markers, onMarkerSelect, setHovered, setSelected]);

  useEffect(() => {
    if (lastSelectionSource !== "map") {
      return;
    }

    lastMapSelectionRef.current = {
      id: selectedId,
      at: lastSelectionAt ?? Date.now(),
    };
  }, [lastSelectionAt, lastSelectionSource, selectedId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    if (pendingPanRef.current !== null) {
      window.clearTimeout(pendingPanRef.current);
      pendingPanRef.current = null;
    }

    if (selectedId === null) {
      return;
    }

    if (!lastSelectionSource) {
      return;
    }

    if (lastSelectionSource === "map") {
      return;
    }

    if (isUserDraggingRef.current) {
      return;
    }

    if (lastSelectionSource === "list") {
      const lastMapSelection = lastMapSelectionRef.current;
      if (
        lastMapSelection.id === selectedId &&
        lastMapSelection.at !== null &&
        lastSelectionAt !== null &&
        lastSelectionAt - lastMapSelection.at < 750
      ) {
        return;
      }
    }

    const targetGym = markers.find(gym => gym.id === selectedId);
    if (!targetGym) {
      return;
    }

    const schedulePan = () => {
      const activeMap = mapRef.current;
      if (!activeMap) {
        return;
      }

      const currentZoom = activeMap.getZoom();
      const targetZoom =
        currentZoom < DEFAULT_ZOOM ? Math.min(DEFAULT_ZOOM, currentZoom + 2) : currentZoom;

      suppressMoveRef.current = true;
      activeMap.easeTo({
        center: [targetGym.longitude, targetGym.latitude],
        zoom: targetZoom,
        duration: 500,
      });
    };

    pendingPanRef.current = window.setTimeout(schedulePan, 120);

    return () => {
      if (pendingPanRef.current !== null) {
        window.clearTimeout(pendingPanRef.current);
        pendingPanRef.current = null;
      }
    };
  }, [lastSelectionAt, lastSelectionSource, markers, selectedId]);

  useEffect(() => {
    markerMapRef.current.forEach(({ element }, id) => {
      const isHovered = id === hoveredId;
      const isSelected = id === selectedId;

      MARKER_HOVERED_CLASSES.forEach(cls => {
        if (isHovered) {
          element.classList.add(cls);
        } else {
          element.classList.remove(cls);
        }
      });

      MARKER_SELECTED_CLASSES.forEach(cls => {
        if (isSelected) {
          element.classList.add(cls);
        } else {
          element.classList.remove(cls);
        }
      });

      element.style.zIndex = isSelected ? "30" : isHovered ? "20" : "10";
      element.dataset.state = isSelected ? "selected" : isHovered ? "hovered" : "default";
    });
  }, [hoveredId, selectedId]);

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
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

const formatArea = (gym: NearbyGym) => {
  const pref = formatSlug(gym.prefecture);
  const city = formatSlug(gym.city);
  const joined = [pref, city].filter(Boolean).join(" / ");
  return joined || "エリア不明";
};
