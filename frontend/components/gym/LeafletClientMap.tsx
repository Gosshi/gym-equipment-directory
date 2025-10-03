"use client";

import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import L, { type LatLngExpression } from "leaflet";

const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

interface LeafletClientMapProps {
  lat: number;
  lng: number;
  name: string;
  address: string;
}

export function LeafletClientMap({ lat, lng, name, address }: LeafletClientMapProps) {
  const center: LatLngExpression = [lat, lng];

  return (
    <MapContainer
      center={center}
      scrollWheelZoom={false}
      style={{ height: "100%", width: "100%" }}
      zoom={16}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Marker icon={icon} position={center}>
        <Popup>
          <strong>{name}</strong>
          <br />
          {address}
        </Popup>
      </Marker>
    </MapContainer>
  );
}

export default LeafletClientMap;
