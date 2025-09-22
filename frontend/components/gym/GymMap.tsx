import Link from "next/link";
import { MapPin } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

interface GymMapProps {
  name: string;
  address?: string;
  latitude?: number;
  longitude?: number;
}

export function GymMap({ name, address, latitude, longitude }: GymMapProps) {
  const hasCoordinates = typeof latitude === "number" && typeof longitude === "number";
  const query = hasCoordinates
    ? `${latitude},${longitude}`
    : address
      ? `${address}`
      : undefined;

  const mapUrl = query
    ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`
    : undefined;

  return (
    <Card>
      <CardHeader>
        <CardTitle>地図</CardTitle>
        <CardDescription>所在地の確認やルート検索にご利用ください。</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="relative overflow-hidden rounded-lg border bg-muted/40">
          <div className="flex aspect-[4/3] items-center justify-center">
            <div className="flex flex-col items-center gap-2 text-muted-foreground">
              <MapPin aria-hidden className="h-8 w-8" />
              <span className="text-sm font-medium">{name}</span>
              <span className="text-xs text-muted-foreground/80">
                {address ?? "地図情報は現在準備中です。"}
              </span>
            </div>
          </div>
        </div>
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
