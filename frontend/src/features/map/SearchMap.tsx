"use client";

import { useEffect } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMapEvents } from "react-leaflet";
import L, { type LatLngExpression } from "leaflet";
import "leaflet/dist/leaflet.css";
import type { GymSummary } from "@/types/gym";

const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

export interface SearchMapProps {
  items: GymSummary[];
  onBoundsChange: (bounds: {
    minLat: number;
    maxLat: number;
    minLng: number;
    maxLng: number;
  }) => void;
  initialCenter?: { lat: number; lng: number };
  initialZoom?: number;
}

function MapEvents({ onBoundsChange }: { onBoundsChange: SearchMapProps["onBoundsChange"] }) {
  const map = useMapEvents({
    moveend: () => {
      const bounds = map.getBounds();
      onBoundsChange({
        minLat: bounds.getSouth(),
        maxLat: bounds.getNorth(),
        minLng: bounds.getWest(),
        maxLng: bounds.getEast(),
      });
    },
  });

  useEffect(() => {
    map.invalidateSize();
    // Trigger initial bounds calculation
    const bounds = map.getBounds();
    onBoundsChange({
      minLat: bounds.getSouth(),
      maxLat: bounds.getNorth(),
      minLng: bounds.getWest(),
      maxLng: bounds.getEast(),
    });
  }, [map, onBoundsChange]);

  return null;
}

export default function SearchMap({
  items,
  onBoundsChange,
  initialCenter,
  initialZoom,
}: SearchMapProps) {
  const defaultCenter: LatLngExpression = [35.681236, 139.767125]; // Tokyo Station
  const center: LatLngExpression = initialCenter
    ? [initialCenter.lat, initialCenter.lng]
    : defaultCenter;

  return (
    <div style={{ height: "100%", width: "100%" }}>
      <MapContainer
        center={center}
        zoom={initialZoom ?? 13}
        scrollWheelZoom={true}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapEvents onBoundsChange={onBoundsChange} />
        {items.map(gym => {
          if (!gym.latitude || !gym.longitude) return null;
          return (
            <Marker
              key={gym.id}
              position={[Number(gym.latitude), Number(gym.longitude)] as LatLngExpression}
              icon={icon}
            >
              <Popup>
                <div className="text-sm">
                  <div className="font-bold mb-1">{gym.name}</div>
                  <div className="text-xs text-gray-600 mb-2">{gym.address}</div>
                  <a
                    href={`/gyms/${gym.slug}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    詳細を見る
                  </a>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
