"use client";

import { useEffect, useMemo, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import { FALLBACK_LOCATION } from "@/hooks/useGymSearch";
import type { GymSummary } from "@/types/gym";

interface SearchResultsMapProps {
  gyms: GymSummary[];
  selectedGymId: string | null;
  hoveredGymId?: string | null;
  onSelect: (slug: string) => void;
  onHover?: (slug: string | null) => void;
  className?: string;
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
      maxzoom: 19,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright" rel="noopener noreferrer" target="_blank">OpenStreetMap</a> contributors',
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
      return JSON.parse(inline) as maplibregl.StyleSpecification;
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

const MARKER_BASE_CLASS =
  "search-map-marker flex h-9 w-9 items-center justify-center rounded-full border-2 border-primary/50 bg-background text-lg shadow-[0_6px_14px_rgba(0,0,0,0.18)] transition focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary";
const MARKER_SELECTED_CLASSES = [
  "bg-primary",
  "text-primary-foreground",
  "border-primary",
  "scale-110",
  "shadow-lg",
];
const MARKER_HOVERED_CLASSES = ["ring-2", "ring-primary", "ring-offset-2"];
const SELECTED_ZOOM = 15;
const FLY_ANIMATION_DURATION = 480;
const COORDINATE_EPSILON = 0.00001;

const hasFiniteCoordinates = (gym: GymSummary): gym is GymSummary & {
  latitude: number;
  longitude: number;
} =>
  typeof gym.latitude === "number" &&
  Number.isFinite(gym.latitude) &&
  typeof gym.longitude === "number" &&
  Number.isFinite(gym.longitude);

const buildMarkerLabel = (gym: GymSummary) => {
  const prefecture = gym.prefecture?.trim() ?? "";
  const city = gym.city?.trim() ?? "";
  const address = gym.address?.trim() ?? "";
  const area = [prefecture, city].filter(Boolean).join(" / ");
  const areaLabel = area || "エリア不明";
  return `${gym.name}（${areaLabel}${address ? ` / ${address}` : ""}）`;
};

export function SearchResultsMap({
  gyms,
  selectedGymId,
  hoveredGymId = null,
  onSelect,
  onHover,
  className,
}: SearchResultsMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef(
    new Map<string, { marker: maplibregl.Marker; element: HTMLButtonElement }>(),
  );
  const boundsSignatureRef = useRef<string | null>(null);
  const mapStyle = useMemo(() => resolveMapStyle(), []);
  const gymsWithCoordinates = useMemo(
    () => gyms.filter(hasFiniteCoordinates),
    [gyms],
  );
  const selectedGym = useMemo(
    () => gymsWithCoordinates.find(gym => gym.slug === selectedGymId) ?? null,
    [gymsWithCoordinates, selectedGymId],
  );

  const lastCenteredRef = useRef<{ slug: string | null; lat: number | null; lng: number | null }>(
    { slug: null, lat: null, lng: null },
  );

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    const initialCenter = selectedGym
      ? { lat: selectedGym.latitude, lng: selectedGym.longitude }
      : gymsWithCoordinates[0]
        ? { lat: gymsWithCoordinates[0].latitude, lng: gymsWithCoordinates[0].longitude }
        : { lat: FALLBACK_LOCATION.lat, lng: FALLBACK_LOCATION.lng };

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: mapStyle,
      center: [initialCenter.lng, initialCenter.lat],
      zoom: selectedGym ? SELECTED_ZOOM : 11,
      scrollZoom: true,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

    const handleResize = () => map.resize();
    window.addEventListener("resize", handleResize);

    mapRef.current = map;
    const markerStore = markersRef.current;

    return () => {
      window.removeEventListener("resize", handleResize);
      markerStore.forEach(({ marker }) => marker.remove());
      markerStore.clear();
      map.remove();
      mapRef.current = null;
    };
  }, [gymsWithCoordinates, mapStyle, selectedGym]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const activeSlugs = new Set(gymsWithCoordinates.map(gym => gym.slug));
    markersRef.current.forEach((value, slug) => {
      if (!activeSlugs.has(slug)) {
        value.marker.remove();
        markersRef.current.delete(slug);
      }
    });

    gymsWithCoordinates.forEach(gym => {
      const existing = markersRef.current.get(gym.slug);
      if (existing) {
        existing.marker.setLngLat([gym.longitude, gym.latitude]);
        return;
      }

      const element = document.createElement("button");
      element.type = "button";
      element.className = MARKER_BASE_CLASS;
      element.textContent = "📍";
      element.title = buildMarkerLabel(gym);
      element.setAttribute("data-gym-slug", gym.slug);
      element.setAttribute("aria-label", `${gym.name} の詳細を開く`);
      element.setAttribute("aria-pressed", selectedGymId === gym.slug ? "true" : "false");

      element.addEventListener("mouseenter", () => onHover?.(gym.slug));
      element.addEventListener("mouseleave", () => onHover?.(null));
      element.addEventListener("focus", () => onHover?.(gym.slug));
      element.addEventListener("blur", () => onHover?.(null));
      element.addEventListener("click", () => onSelect(gym.slug));

      const marker = new maplibregl.Marker({ element, anchor: "bottom" })
        .setLngLat([gym.longitude, gym.latitude])
        .addTo(map);

      markersRef.current.set(gym.slug, { marker, element });
    });
  }, [gymsWithCoordinates, onHover, onSelect, selectedGymId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    if (selectedGymId) {
      boundsSignatureRef.current = null;
      return;
    }

    if (gymsWithCoordinates.length === 0) {
      boundsSignatureRef.current = null;
      return;
    }

    const signature = gymsWithCoordinates.map(gym => gym.slug).join("|");
    if (boundsSignatureRef.current === signature) {
      return;
    }

    const bounds = new maplibregl.LngLatBounds();
    gymsWithCoordinates.forEach(gym => {
      bounds.extend([gym.longitude, gym.latitude]);
    });

    if (bounds.isEmpty()) {
      return;
    }

    boundsSignatureRef.current = signature;
    map.fitBounds(bounds, { padding: 60, maxZoom: 13, duration: 400 });
  }, [gymsWithCoordinates, selectedGymId]);

  useEffect(() => {
    markersRef.current.forEach(({ element }, slug) => {
      const isSelected = slug === selectedGymId;
      const isHovered = slug === hoveredGymId;

      element.setAttribute("aria-pressed", isSelected ? "true" : "false");
      element.dataset.state = isSelected ? "selected" : isHovered ? "hovered" : "default";

      MARKER_SELECTED_CLASSES.forEach(cls => {
        if (isSelected) {
          element.classList.add(cls);
        } else {
          element.classList.remove(cls);
        }
      });

      MARKER_HOVERED_CLASSES.forEach(cls => {
        if (!isSelected && isHovered) {
          element.classList.add(cls);
        } else {
          element.classList.remove(cls);
        }
      });

      element.style.zIndex = isSelected ? "30" : isHovered ? "20" : "10";
    });
  }, [hoveredGymId, selectedGymId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedGym) {
      return;
    }

    const last = lastCenteredRef.current;
    if (
      last.slug === selectedGym.slug &&
      last.lat != null &&
      last.lng != null &&
      Math.abs(last.lat - selectedGym.latitude) < COORDINATE_EPSILON &&
      Math.abs(last.lng - selectedGym.longitude) < COORDINATE_EPSILON
    ) {
      return;
    }

    const currentCenter = map.getCenter();
    const sameLat = Math.abs(currentCenter.lat - selectedGym.latitude) < COORDINATE_EPSILON;
    const sameLng = Math.abs(currentCenter.lng - selectedGym.longitude) < COORDINATE_EPSILON;

    if (sameLat && sameLng && map.getZoom() >= SELECTED_ZOOM) {
      lastCenteredRef.current = {
        slug: selectedGym.slug,
        lat: selectedGym.latitude,
        lng: selectedGym.longitude,
      };
      return;
    }

    const targetZoom = Math.max(map.getZoom(), SELECTED_ZOOM);
    map.flyTo({
      center: [selectedGym.longitude, selectedGym.latitude],
      zoom: targetZoom,
      duration: FLY_ANIMATION_DURATION,
    });

    lastCenteredRef.current = {
      slug: selectedGym.slug,
      lat: selectedGym.latitude,
      lng: selectedGym.longitude,
    };
  }, [selectedGym]);

  return (
    <div
      aria-label="ジム検索結果の地図"
      className={className}
      data-testid="search-results-map"
      ref={containerRef}
      role="presentation"
      style={{ minHeight: "320px", borderRadius: "1rem", overflow: "hidden" }}
    />
  );
}

export default SearchResultsMap;
