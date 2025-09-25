"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { createRoot, type Root } from "react-dom/client";
import maplibregl from "maplibre-gl";
import type { StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import { GymPopup, type GymPopupData, type GymPopupMode } from "@/components/map/GymPopup";
import type { MapInteractionSource } from "@/state/mapSelection";
import type { NearbyGym } from "@/types/gym";

export interface NearbyMapProps {
  center: { lat: number; lng: number };
  markers: NearbyGym[];
  hoveredGymId: number | null;
  selectedGymId: number | null;
  lastSelectionSource: MapInteractionSource | null;
  lastSelectionAt: number | null;
  onCenterChange: (nextCenter: { lat: number; lng: number }) => void;
  onSelect: (gymId: number | null, source: MapInteractionSource) => void;
  onPreview: (gymId: number | null, source: MapInteractionSource) => void;
  onRequestDetail: (gym: NearbyGym) => void;
  popupSupplements?: Record<number, Partial<GymPopupData>>;
  popupIsLoading?: boolean;
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
  hoveredGymId,
  selectedGymId,
  lastSelectionSource,
  lastSelectionAt,
  onCenterChange,
  onSelect,
  onPreview,
  onRequestDetail,
  popupSupplements = {},
  popupIsLoading = false,
  zoom = DEFAULT_ZOOM,
}: NearbyMapProps) {

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
  const popupRef = useRef<
    | {
        popup: maplibregl.Popup;
        container: HTMLDivElement;
        root: Root;
        gymId: number | null;
        mode: GymPopupMode;
        closeHandler: () => void;
      }
    | null
  >(null);

  const cleanupPopup = useCallback((removePopup: boolean) => {
    const entry = popupRef.current;
    if (!entry) {
      return;
    }
    entry.popup.off("close", entry.closeHandler);
    if (removePopup) {
      entry.popup.remove();
    }
    entry.root.unmount();
    popupRef.current = null;
  }, []);

  useEffect(
    () => () => {
      if (pendingPanRef.current !== null) {
        window.clearTimeout(pendingPanRef.current);
        pendingPanRef.current = null;
      }
      cleanupPopup(true);
    },
    [cleanupPopup],
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

      element.addEventListener("mouseenter", () => onPreview(gym.id, "map"));
      element.addEventListener("mouseleave", () => onPreview(null, "map"));
      element.addEventListener("focus", () => onPreview(gym.id, "map"));
      element.addEventListener("blur", () => onPreview(null, "map"));
      element.addEventListener("click", () => {
        onSelect(gym.id, "map");
      });

      const marker = new maplibregl.Marker({ element, anchor: "bottom" })
        .setLngLat([gym.longitude, gym.latitude])
        .addTo(map);

      markerMapRef.current.set(gym.id, { marker, element });
    });
  }, [markers, onPreview, onSelect]);

  useEffect(() => {
    if (lastSelectionSource !== "map") {
      return;
    }

    lastMapSelectionRef.current = {
      id: selectedGymId,
      at: lastSelectionAt ?? Date.now(),
    };
  }, [lastSelectionAt, lastSelectionSource, selectedGymId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    if (pendingPanRef.current !== null) {
      window.clearTimeout(pendingPanRef.current);
      pendingPanRef.current = null;
    }

    if (selectedGymId === null) {
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
        lastMapSelection.id === selectedGymId &&
        lastMapSelection.at !== null &&
        lastSelectionAt !== null &&
        lastSelectionAt - lastMapSelection.at < 750
      ) {
        return;
      }
    }

    const targetGym = markers.find(gym => gym.id === selectedGymId);
    if (!targetGym) {
      return;
    }

    const schedulePan = () => {
      const activeMap = mapRef.current;
      if (!activeMap) {
        return;
      }

      if (isUserDraggingRef.current) {
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
  }, [lastSelectionAt, lastSelectionSource, markers, selectedGymId]);

  useEffect(() => {
    markerMapRef.current.forEach(({ element }, id) => {
      const isHovered = id === hoveredGymId;
      const isSelected = id === selectedGymId;

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
  }, [hoveredGymId, selectedGymId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const previewId =
      hoveredGymId !== null && hoveredGymId !== selectedGymId ? hoveredGymId : null;
    const activeId = previewId ?? selectedGymId;
    const mode: GymPopupMode | null =
      previewId !== null ? "preview" : selectedGymId !== null ? "selected" : null;

    if (activeId == null || mode == null) {
      cleanupPopup(true);
      return;
    }

    const gym = markers.find(item => item.id === activeId);
    if (!gym) {
      cleanupPopup(true);
      return;
    }

    const notifyClose = () => {
      if (mode === "preview") {
        onPreview(null, "map");
      } else {
        onSelect(null, "map");
      }
    };

    const supplement = popupSupplements[activeId] ?? {};
    const popupData = composePopupData(gym, supplement);

    const existing = popupRef.current;
    if (!existing) {
      const container = document.createElement("div");
      container.className = "gym-popup-container";
      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: true,
        offset: 18,
        anchor: "bottom",
      });
      popup.setDOMContent(container);
      const root = createRoot(container);
      const closeHandler = () => {
        cleanupPopup(false);
        notifyClose();
      };
      popup.on("close", closeHandler);
      popupRef.current = {
        popup,
        container,
        root,
        gymId: activeId,
        mode,
        closeHandler,
      };
      popup.setLngLat([gym.longitude, gym.latitude]).addTo(map);
    } else {
      if (existing.gymId !== activeId || existing.mode !== mode) {
        existing.popup.off("close", existing.closeHandler);
        const closeHandler = () => {
          cleanupPopup(false);
          notifyClose();
        };
        existing.closeHandler = closeHandler;
        existing.popup.on("close", closeHandler);
        existing.gymId = activeId;
        existing.mode = mode;
      }
      existing.popup.setLngLat([gym.longitude, gym.latitude]);
    }

    const current = popupRef.current;
    if (!current) {
      return;
    }

    const handleViewDetail = () => {
      if (mode === "preview") {
        onSelect(gym.id, "map");
      }
      onRequestDetail(gym);
    };

    const handleCloseClick = () => {
      cleanupPopup(true);
      notifyClose();
    };

    current.root.render(
      <GymPopup
        data={popupData}
        mode={mode}
        isLoading={mode === "selected" ? popupIsLoading : false}
        onClose={handleCloseClick}
        onViewDetail={handleViewDetail}
      />,
    );

    if (!current.popup.isOpen()) {
      current.popup.addTo(map);
    }

    window.requestAnimationFrame(() => {
      const dialog = current.container.querySelector('[role="dialog"]');
      if (dialog instanceof HTMLElement) {
        dialog.focus();
      }
    });

    return () => {
      const entry = popupRef.current;
      if (entry && !entry.popup.isOpen()) {
        entry.root.render(null);
      }
    };
  }, [
    hoveredGymId,
    selectedGymId,
    markers,
    popupSupplements,
    popupIsLoading,
    onPreview,
    onSelect,
    onRequestDetail,
    cleanupPopup,
  ]);

  return <div className="h-[420px] w-full rounded-lg border" ref={containerRef} />;
}

const composePopupData = (
  gym: NearbyGym,
  supplement: Partial<GymPopupData>,
): GymPopupData => ({
  id: gym.id,
  slug: gym.slug,
  name: gym.name,
  latitude: gym.latitude,
  longitude: gym.longitude,
  prefecture: gym.prefecture,
  city: gym.city,
  distanceKm: gym.distanceKm,
  ...supplement,
});

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
