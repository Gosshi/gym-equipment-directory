"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import type { StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { createGymClusterIndex, getClusterExpansionZoom, getMarkersForBounds } from "@/lib/cluster";
import type { MapViewport } from "@/hooks/useVisibleGyms";
import type { MapInteractionSource } from "@/state/mapSelection";
import type { NearbyGym } from "@/types/gym";

export interface NearbyMapProps {
  center: { lat: number; lng: number };
  markers: NearbyGym[];
  selectedGymId: number | null;
  lastSelectionSource: MapInteractionSource | null;
  lastSelectionAt: number | null;
  onCenterChange: (nextCenter: { lat: number; lng: number }) => void;
  onSelect: (gymId: number | null, source: MapInteractionSource) => void;
  onViewportChange?: (viewport: MapViewport) => void;
  zoom?: number;
  markersStatus?: "idle" | "loading" | "success" | "error";
  markersIsLoading?: boolean;
  markersIsInitialLoading?: boolean;
  markersError?: string | null;
  onRetryMarkers?: () => void;
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
const CLUSTER_THRESHOLD = 50;
const MARKER_BASE_CLASS =
  "nearby-marker flex h-11 w-11 items-center justify-center rounded-full border-2 border-red-400/70 bg-white/90 text-3xl text-red-500 shadow-[0_8px_18px_rgba(0,0,0,0.15)] backdrop-blur-sm transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-red-500";
const MARKER_SELECTED_CLASSES = Object.freeze([
  "border-red-500",
  "bg-red-500",
  "text-white",
  "scale-125",
  "shadow-lg",
]);
const CLUSTER_BASE_CLASS =
  "nearby-cluster flex h-14 w-14 items-center justify-center rounded-full border-2 border-primary bg-primary text-base font-semibold text-primary-foreground shadow-[0_10px_24px_rgba(0,0,0,0.2)] transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary hover:scale-105";
const CLUSTER_HOVERED_CLASSES = Object.freeze(["ring-4", "ring-primary/70", "ring-offset-2"]);

type MarkerEntry = {
  marker: maplibregl.Marker;
  element: HTMLButtonElement;
  type: "gym" | "cluster";
  id: number;
};

const roundCoordinate = (value: number) => Number.parseFloat(value.toFixed(6));

const readViewport = (map: maplibregl.Map): MapViewport => {
  const bounds = map.getBounds();
  const center = map.getCenter();
  return {
    bounds: {
      north: roundCoordinate(bounds.getNorth()),
      south: roundCoordinate(bounds.getSouth()),
      east: roundCoordinate(bounds.getEast()),
      west: roundCoordinate(bounds.getWest()),
    },
    center: {
      lat: roundCoordinate(center.lat),
      lng: roundCoordinate(center.lng),
    },
    zoom: map.getZoom(),
  };
};

const createGymMarkerElement = (
  gym: NearbyGym,
  onSelect: (gymId: number | null, source: MapInteractionSource) => void,
): HTMLButtonElement => {
  const element = document.createElement("button");
  element.type = "button";
  element.className = MARKER_BASE_CLASS;
  element.textContent = "📍";
  element.setAttribute("aria-label", `${gym.name} の詳細を開く`);
  element.title = buildTooltip(gym);
  element.style.zIndex = "10";
  element.dataset.gymId = String(gym.id);
  element.dataset.markerType = "gym";
  element.dataset.state = "default";
  element.dataset.panelAnchor = "pin";

  element.addEventListener("click", () => {
    onSelect(gym.id, "map");
  });

  return element;
};

const updateGymMarkerElement = (element: HTMLButtonElement, gym: NearbyGym) => {
  element.dataset.gymId = String(gym.id);
  element.setAttribute("aria-label", `${gym.name} の詳細を開く`);
  element.title = buildTooltip(gym);
};

const createClusterMarkerElement = (count: number, onClick: () => void): HTMLButtonElement => {
  const element = document.createElement("button");
  element.type = "button";
  element.className = CLUSTER_BASE_CLASS;
  element.textContent = String(count);
  element.dataset.markerType = "cluster";
  element.dataset.count = String(count);
  element.dataset.panelAnchor = "cluster";
  element.setAttribute("aria-label", `周辺のジム ${count}件`);
  element.style.zIndex = "15";
  element.addEventListener("click", onClick);
  const activate = () => {
    CLUSTER_HOVERED_CLASSES.forEach(cls => element.classList.add(cls));
  };
  const deactivate = () => {
    CLUSTER_HOVERED_CLASSES.forEach(cls => element.classList.remove(cls));
  };
  element.addEventListener("mouseenter", activate);
  element.addEventListener("mouseleave", deactivate);
  element.addEventListener("focus", activate);
  element.addEventListener("blur", deactivate);
  return element;
};

const updateClusterMarkerElement = (element: HTMLButtonElement, count: number) => {
  element.textContent = String(count);
  element.dataset.count = String(count);
};

const logMapCenter = (payload: Record<string, unknown>) => {
  if (typeof window !== "undefined" && process.env.NODE_ENV !== "test") {
    // eslint-disable-next-line no-console
    console.debug("map_center_changed", payload);
  }
};

export function NearbyMap({
  center,
  markers,
  selectedGymId,
  lastSelectionSource,
  lastSelectionAt,
  onCenterChange,
  onSelect,
  onViewportChange,
  zoom = DEFAULT_ZOOM,
  markersStatus = "idle",
  markersIsLoading = false,
  markersIsInitialLoading = false,
  markersError = null,
  onRetryMarkers,
}: NearbyMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerMapRef = useRef(new Map<string, MarkerEntry>());
  const suppressMoveRef = useRef(false);
  const isUserDraggingRef = useRef(false);
  const isUserInteractingRef = useRef(false);
  const pendingPanRef = useRef<number | null>(null);
  const resumePendingAutoPanRef = useRef<(() => void) | null>(null);
  const userInteractionTimeoutRef = useRef<number | null>(null);
  const lastDragStartAtRef = useRef<number | null>(null);
  const lastAutoPanRef = useRef<{ id: number | null; at: number | null }>({
    id: null,
    at: null,
  });
  const lastMapSelectionRef = useRef<{ id: number | null; at: number | null }>({
    id: null,
    at: null,
  });
  const [zoomLevel, setZoomLevel] = useState(() => zoom);
  const [isMapReady, setIsMapReady] = useState(false);
  const clusterIndex = useMemo(
    () => createGymClusterIndex(markers, { minClusterCount: CLUSTER_THRESHOLD }),
    [markers],
  );
  const clusterIndexRef = useRef(clusterIndex);
  const onCenterChangeRef = useRef(onCenterChange);
  const onSelectRef = useRef(onSelect);
  const onViewportChangeRef = useRef(onViewportChange);
  const initialCenterRef = useRef<{ lat: number; lng: number } | null>(null);
  const initialZoomRef = useRef<number | null>(null);

  if (initialCenterRef.current === null) {
    initialCenterRef.current = { lat: center.lat, lng: center.lng };
  }

  if (initialZoomRef.current === null) {
    initialZoomRef.current = zoom;
  }

  useEffect(() => {
    clusterIndexRef.current = clusterIndex;
  }, [clusterIndex]);

  useEffect(() => {
    onCenterChangeRef.current = onCenterChange;
  }, [onCenterChange]);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    onViewportChangeRef.current = onViewportChange;
  }, [onViewportChange]);

  const markUserInteraction = useCallback(() => {
    isUserInteractingRef.current = true;
    if (userInteractionTimeoutRef.current !== null) {
      window.clearTimeout(userInteractionTimeoutRef.current);
    }
    userInteractionTimeoutRef.current = window.setTimeout(() => {
      isUserInteractingRef.current = false;
      userInteractionTimeoutRef.current = null;
      if (pendingPanRef.current !== null) {
        const pending = pendingPanRef.current;
        pendingPanRef.current = null;
        window.clearTimeout(pending);
        resumePendingAutoPanRef.current?.();
      }
    }, 600);
  }, []);

  const handleClusterExpand = useCallback(
    (clusterId: number, coordinates: [number, number]) => {
      const map = mapRef.current;
      const clusterStore = clusterIndexRef.current;
      if (!map || !clusterStore) {
        return;
      }
      const nextZoom = getClusterExpansionZoom(clusterStore, clusterId);
      const currentZoom = map.getZoom();
      const resolvedZoom =
        nextZoom != null && Number.isFinite(nextZoom)
          ? Math.min(nextZoom, 18)
          : Math.min(currentZoom + 2, 18);
      markUserInteraction();
      suppressMoveRef.current = true;
      map.easeTo({ center: coordinates, zoom: resolvedZoom, duration: 420 });
    },
    [markUserInteraction],
  );

  const emitSelect = useCallback(
    (gymId: number | null, source: MapInteractionSource) => {
      onSelectRef.current(gymId, source);
    },
    [],
  );

  const updateMarkersForViewport = useCallback(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const clusterStore = clusterIndexRef.current;
    if (!clusterStore) {
      return;
    }

    const viewport = readViewport(map);
    const features = getMarkersForBounds(clusterStore, viewport.bounds, viewport.zoom);
    const nextKeys = new Set<string>();
    const store = markerMapRef.current;

    features.forEach(feature => {
      const key = feature.type === "cluster" ? `cluster-${feature.id}` : `gym-${feature.id}`;
      nextKeys.add(key);
      const existing = store.get(key);
      if (existing) {
        existing.marker.setLngLat(feature.coordinates);
        if (feature.type === "cluster") {
          updateClusterMarkerElement(existing.element, feature.count);
        } else {
          updateGymMarkerElement(existing.element, feature.gym);
        }
        return;
      }

      if (feature.type === "cluster") {
        const element = createClusterMarkerElement(feature.count, () => {
          handleClusterExpand(feature.id, feature.coordinates);
        });
        const marker = new maplibregl.Marker({ element, anchor: "bottom" })
          .setLngLat(feature.coordinates)
          .addTo(map);
        store.set(key, { marker, element, type: "cluster", id: feature.id });
      } else {
        const element = createGymMarkerElement(feature.gym, emitSelect);
        const marker = new maplibregl.Marker({ element, anchor: "bottom" })
          .setLngLat(feature.coordinates)
          .addTo(map);
        store.set(key, { marker, element, type: "gym", id: feature.gym.id });
      }
    });

    store.forEach((entry, key) => {
      if (!nextKeys.has(key)) {
        entry.marker.remove();
        store.delete(key);
      }
    });
  }, [emitSelect, handleClusterExpand]);

  const notifyViewportChange = useCallback(() => {
    const handler = onViewportChangeRef.current;
    if (!handler) {
      return;
    }
    const map = mapRef.current;
    if (!map) {
      return;
    }
    const viewport = readViewport(map);
    handler(viewport);
  }, []);

  useEffect(
    () => () => {
      if (pendingPanRef.current !== null) {
        window.clearTimeout(pendingPanRef.current);
        pendingPanRef.current = null;
      }
      if (userInteractionTimeoutRef.current !== null) {
        window.clearTimeout(userInteractionTimeoutRef.current);
        userInteractionTimeoutRef.current = null;
      }
    },
    [],
  );

  const mapStyle = useMemo(() => resolveMapStyle(), []);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    const initialCenter = initialCenterRef.current;
    const initialZoom = initialZoomRef.current;
    if (!initialCenter || initialZoom == null) {
      return;
    }
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: mapStyle,
      center: [initialCenter.lng, initialCenter.lat],
      zoom: initialZoom,
      scrollZoom: true,
      dragPan: true,
      touchZoomRotate: true,
      doubleClickZoom: true,
      keyboard: true,
      maxZoom: 19,
      minZoom: 3,
    });
    const markerStore = markerMapRef.current;

    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false, visualizePitch: false }),
      "top-right",
    );

    const handleMapClick = (event: maplibregl.MapMouseEvent) => {
      const target = event.originalEvent?.target;
      if (target instanceof HTMLElement) {
        if (
          target.closest(".nearby-marker") ||
          target.closest(".nearby-cluster") ||
          target.closest(".maplibregl-ctrl") ||
          target.closest('[data-panel-anchor="pin"]')
        ) {
          return;
        }
      }
      emitSelect(null, "map");
    };
    map.on("click", handleMapClick);

    const handleMoveEnd = () => {
      updateMarkersForViewport();
      notifyViewportChange();
      if (suppressMoveRef.current) {
        suppressMoveRef.current = false;
        return;
      }
      const next = map.getCenter();
      const payload = { lat: Number(next.lat.toFixed(6)), lng: Number(next.lng.toFixed(6)) };
      logMapCenter({ ...payload, zoom: map.getZoom() });
      onCenterChangeRef.current(payload);
    };

    const handleWheel = () => {
      markUserInteraction();
    };

    const handleTouchStart = () => {
      markUserInteraction();
    };

    const handleTouchMove = () => {
      markUserInteraction();
    };

    const handleDoubleClick = () => {
      markUserInteraction();
    };

    const handleZoomStart = (event: maplibregl.MapLibreEvent<unknown>) => {
      if (event?.originalEvent) {
        markUserInteraction();
      }
    };

    const handleZoomEnd = () => {
      const nextZoom = Number.parseFloat(map.getZoom().toFixed(2));
      setZoomLevel(nextZoom);
    };

    const handleDragStart = () => {
      isUserDraggingRef.current = true;
      markUserInteraction();
      if (pendingPanRef.current !== null) {
        window.clearTimeout(pendingPanRef.current);
        pendingPanRef.current = null;
      }
      lastDragStartAtRef.current = Date.now();
    };

    const handleDragEnd = () => {
      isUserDraggingRef.current = false;
      lastDragStartAtRef.current = null;
      markUserInteraction();
    };

    map.on("moveend", handleMoveEnd);
    map.on("dragstart", handleDragStart);
    map.on("dragend", handleDragEnd);
    map.on("zoomstart", handleZoomStart);
    map.on("zoomend", handleZoomEnd);
    map.on("wheel", handleWheel);
    map.on("touchstart", handleTouchStart);
    map.on("touchmove", handleTouchMove);
    map.on("dblclick", handleDoubleClick);
    const handleLoad = () => {
      updateMarkersForViewport();
      notifyViewportChange();
      setZoomLevel(Number.parseFloat(map.getZoom().toFixed(2)));
      setIsMapReady(true);
    };
    map.on("load", handleLoad);

    mapRef.current = map;
    setIsMapReady(true);

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
      if (userInteractionTimeoutRef.current !== null) {
        window.clearTimeout(userInteractionTimeoutRef.current);
        userInteractionTimeoutRef.current = null;
      }
      isUserDraggingRef.current = false;
      isUserInteractingRef.current = false;
      map.off("click", handleMapClick);
      map.off("moveend", handleMoveEnd);
      map.off("dragstart", handleDragStart);
      map.off("dragend", handleDragEnd);
      map.off("zoomstart", handleZoomStart);
      map.off("zoomend", handleZoomEnd);
      map.off("wheel", handleWheel);
      map.off("touchstart", handleTouchStart);
      map.off("touchmove", handleTouchMove);
      map.off("dblclick", handleDoubleClick);
      map.off("load", handleLoad);
      map.remove();
      mapRef.current = null;
      setIsMapReady(false);
    };
  }, [emitSelect, mapStyle, markUserInteraction, notifyViewportChange, updateMarkersForViewport]);

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
    updateMarkersForViewport();
  }, [updateMarkersForViewport]);

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
    resumePendingAutoPanRef.current = null;

    if (selectedGymId === null) {
      lastAutoPanRef.current = { id: null, at: null };
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

    if (
      lastDragStartAtRef.current !== null &&
      lastSelectionAt !== null &&
      lastSelectionAt - lastDragStartAtRef.current < 400
    ) {
      return;
    }

    const lastAutoPan = lastAutoPanRef.current;
    if (
      lastAutoPan.id === selectedGymId &&
      lastAutoPan.at !== null &&
      lastSelectionAt !== null &&
      lastAutoPan.at >= lastSelectionAt
    ) {
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

    const targetGymId = selectedGymId;
    const targetGym = markers.find(gym => gym.id === targetGymId);
    if (!targetGym) {
      return;
    }

    const schedulePan = () => {
      const activeMap = mapRef.current;
      if (!activeMap) {
        pendingPanRef.current = null;
        return;
      }

      if (isUserDraggingRef.current) {
        pendingPanRef.current = window.setTimeout(schedulePan, 240);
        return;
      }

      const currentZoom = activeMap.getZoom();
      const targetZoom =
        currentZoom < DEFAULT_ZOOM ? Math.min(DEFAULT_ZOOM, currentZoom + 2) : currentZoom;

      if (isUserInteractingRef.current) {
        pendingPanRef.current = window.setTimeout(schedulePan, 300);
        return;
      }

      pendingPanRef.current = null;
      suppressMoveRef.current = true;
      lastAutoPanRef.current = { id: targetGymId, at: Date.now() };
      activeMap.flyTo({
        center: [targetGym.longitude, targetGym.latitude],
        zoom: targetZoom,
        duration: 480,
        essential: true,
      });
    };

    resumePendingAutoPanRef.current = schedulePan;
    pendingPanRef.current = window.setTimeout(schedulePan, 120);

    return () => {
      resumePendingAutoPanRef.current = null;
      if (pendingPanRef.current !== null) {
        window.clearTimeout(pendingPanRef.current);
        pendingPanRef.current = null;
      }
    };
  }, [lastSelectionAt, lastSelectionSource, markers, selectedGymId]);

  useEffect(() => {
    markerMapRef.current.forEach(entry => {
      if (entry.type !== "gym") {
        return;
      }
      const { element, id } = entry;
      const isSelected = id === selectedGymId;

      MARKER_SELECTED_CLASSES.forEach(cls => {
        if (isSelected) {
          element.classList.add(cls);
        } else {
          element.classList.remove(cls);
        }
      });

      element.style.zIndex = isSelected ? "30" : "10";
      element.dataset.state = isSelected ? "selected" : "default";
    });
  }, [selectedGymId]);

  const handleManualZoom = useCallback(
    (delta: number) => {
      const map = mapRef.current;
      if (!map) {
        return;
      }

      markUserInteraction();
      const nextZoom = map.getZoom() + delta;
      const minZoom = typeof map.getMinZoom === "function" ? map.getMinZoom() : map.getZoom() - 20;
      const maxZoom = typeof map.getMaxZoom === "function" ? map.getMaxZoom() : map.getZoom() + 20;
      const clamped = Math.max(minZoom, Math.min(maxZoom, nextZoom));

      suppressMoveRef.current = true;
      map.easeTo({ zoom: clamped, duration: 240 });
    },
    [markUserInteraction],
  );

  const showSkeletonOverlay = markersIsInitialLoading;
  const showLoadingBadge = markersIsLoading && !markersIsInitialLoading;
  const showErrorOverlay = markersStatus === "error" && Boolean(markersError);

  return (
    <div className="relative">
      <div className="h-[420px] w-full rounded-lg border" ref={containerRef} />
      <span aria-hidden className="sr-only" data-testid="nearby-map-zoom">
        {zoomLevel.toFixed(2)}
      </span>
      <div className="pointer-events-none absolute right-3 top-3 z-30 flex flex-col gap-2">
        <button
          aria-label="地図をズームイン"
          className="pointer-events-auto flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background/90 text-lg font-semibold text-foreground shadow"
          data-testid="nearby-map-zoom-in-button"
          disabled={!isMapReady}
          onClick={() => handleManualZoom(1)}
          type="button"
        >
          +
        </button>
        <button
          aria-label="地図をズームアウト"
          className="pointer-events-auto flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background/90 text-lg font-semibold text-foreground shadow"
          data-testid="nearby-map-zoom-out-button"
          disabled={!isMapReady}
          onClick={() => handleManualZoom(-1)}
          type="button"
        >
          −
        </button>
      </div>
      {showSkeletonOverlay ? (
        <div className="pointer-events-none absolute inset-0 z-20 flex items-center justify-center rounded-lg border border-border/60 bg-background/80 backdrop-blur">
          <div className="flex w-full max-w-sm items-center gap-4 px-6">
            <Skeleton aria-hidden className="h-24 w-24 rounded-full" />
            <div className="flex-1 space-y-3">
              <Skeleton aria-hidden className="h-4 w-3/4" />
              <Skeleton aria-hidden className="h-4 w-2/3" />
              <Skeleton aria-hidden className="h-4 w-1/2" />
            </div>
          </div>
        </div>
      ) : null}
      {showLoadingBadge ? (
        <div className="pointer-events-none absolute left-4 top-4 z-20 flex items-center gap-2 rounded-full bg-background/90 px-3 py-1.5 text-xs font-medium text-muted-foreground shadow">
          <span aria-hidden className="h-2 w-2 animate-pulse rounded-full bg-primary" />
          <span>地図を更新中…</span>
        </div>
      ) : null}
      {showErrorOverlay ? (
        <div className="absolute inset-0 z-30 flex flex-col items-center justify-center gap-3 rounded-lg border border-destructive/40 bg-destructive/10 p-6 text-center text-destructive">
          <p className="text-sm font-semibold">地図のジム取得に失敗しました</p>
          <p className="text-xs text-destructive/80">{markersError}</p>
          {onRetryMarkers ? (
            <Button onClick={onRetryMarkers} type="button" variant="outline" size="sm">
              再試行する
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
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
