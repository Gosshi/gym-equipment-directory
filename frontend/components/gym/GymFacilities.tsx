import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface FacilityGroup {
  category: string;
  items: string[];
}

interface GymFacilitiesProps {
  facilities: FacilityGroup[];
}

export function GymFacilities({ facilities }: GymFacilitiesProps) {
  const hasFacilities = facilities.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>設備</CardTitle>
        <CardDescription>カテゴリごとに登録されている設備一覧です。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {hasFacilities ? (
          facilities.map(group => (
            <section
              aria-label={`${group.category}の設備`}
              className="space-y-3"
              key={group.category}
            >
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {group.category}
              </h3>
              <div className="flex flex-wrap gap-2">
                {group.items.map(item => (
                  <Badge key={`${group.category}-${item}`} variant="outline">
                    {item}
                  </Badge>
                ))}
              </div>
            </section>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">設備情報は現在準備中です。</p>
        )}
      </CardContent>
    </Card>
  );
}
