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

const LeafletMap = dynamic(
  () => import("./LeafletClientMap").then(module => module.LeafletClientMap),
  {
    ssr: false,
    loading: () => <div className="h-full w-full animate-pulse bg-muted" />,
  },
);

interface GymMapProps {
  name: string;
  address?: string;
  latitude?: number;
  longitude?: number;
}

const hasValidCoordinate = (value?: number): value is number =>
  typeof value === "number" && Number.isFinite(value);

export function GymMap({ name, address, latitude, longitude }: GymMapProps) {
  const hasCoordinates = hasValidCoordinate(latitude) && hasValidCoordinate(longitude);

  const mapQuery = hasCoordinates
    ? `${latitude},${longitude}`
    : address
      ? `${address}`
      : undefined;

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
        {hasCoordinates ? (
          <div className="aspect-[4/3] overflow-hidden rounded-lg">
            <LeafletMap
              address={address ?? ""}
              lat={latitude!}
              lng={longitude!}
              name={name}
            />
          </div>
        ) : (
          <div className="flex min-h-[6rem] items-center justify-center rounded-lg border border-dashed">
            <p className="text-sm text-muted-foreground">地図情報なし</p>
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
