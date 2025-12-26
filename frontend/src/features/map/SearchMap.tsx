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
  const map = useMapEvents({});

  useEffect(() => {
    const handleMoveEnd = () => {
      const bounds = map.getBounds();
      onBoundsChange({
        minLat: bounds.getSouth(),
        maxLat: bounds.getNorth(),
        minLng: bounds.getWest(),
        maxLng: bounds.getEast(),
      });
    };

    map.on("moveend", handleMoveEnd);

    // Initial trigger
    map.invalidateSize();
    handleMoveEnd();

    return () => {
      map.off("moveend", handleMoveEnd);
    };
  }, [map, onBoundsChange]);

  return null;
}

import { Locate, Loader2 } from "lucide-react";
import { useState } from "react";
import { useMap } from "react-leaflet";
import { Button } from "@/components/ui/button";

function CurrentLocationControl() {
  const map = useMap();
  const [loading, setLoading] = useState(false);

  const handleLocationClick = () => {
    if (!navigator.geolocation) {
      alert("お使いのブラウザは位置情報をサポートしていません。");
      return;
    }

    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      position => {
        const { latitude, longitude } = position.coords;
        map.flyTo([latitude, longitude], 14, {
          duration: 1.5,
        });
        setLoading(false);
      },
      error => {
        console.error(error);
        alert("位置情報の取得に失敗しました。");
        setLoading(false);
      },
      { timeout: 10000, maximumAge: 0 },
    );
  };

  return (
    <div className="leaflet-bottom leaflet-right">
      <div className="leaflet-control leaflet-bar m-4">
        <Button
          variant="secondary"
          size="icon"
          className="h-10 w-10 shadow-md rounded-lg bg-white hover:bg-gray-100 text-gray-700 border-2 border-gray-300"
          onClick={handleLocationClick}
          disabled={loading}
          title="現在地に移動"
        >
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Locate className="h-5 w-5" />}
        </Button>
      </div>
    </div>
  );
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
        zoomControl={false} // We can add custom zoom control if needed, or leave default top-left
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
        <CurrentLocationControl />
      </MapContainer>
    </div>
  );
}
