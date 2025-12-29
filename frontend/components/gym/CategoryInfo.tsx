import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Waves, LayoutGrid, Building, TreeDeciduous, Dumbbell } from "lucide-react";

interface CategoryInfoProps {
  category?: string | null;
  categories?: string[];
  // Pool
  poolLanes?: number | null;
  poolLengthM?: number | null;
  poolHeated?: boolean | null;
  // Court
  courtType?: string | null;
  courtCount?: number | null;
  courtSurface?: string | null;
  courtLighting?: boolean | null;
  // Hall
  hallSports?: string[];
  hallAreaSqm?: number | null;
  // Field
  fieldType?: string | null;
  fieldCount?: number | null;
  fieldLighting?: boolean | null;
}

const CATEGORY_CONFIG: Record<
  string,
  { label: string; icon: React.ComponentType<{ className?: string }> }
> = {
  gym: { label: "トレーニング室", icon: Dumbbell },
  pool: { label: "プール", icon: Waves },
  court: { label: "コート", icon: LayoutGrid },
  hall: { label: "体育館", icon: Building },
  field: { label: "グラウンド", icon: TreeDeciduous },
};

export function CategoryInfo(props: CategoryInfoProps) {
  const { category, categories = [] } = props;

  // Determine which categories to display
  const categoriesToShow = categories.length > 0 ? categories : category ? [category] : [];

  // Filter out 'gym' as it's handled by GymFacilities
  const nonGymCategories = categoriesToShow.filter(c => c !== "gym");

  if (nonGymCategories.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      {nonGymCategories.map(cat => {
        const config = CATEGORY_CONFIG[cat];
        if (!config) return null;

        const Icon = config.icon;

        return (
          <Card key={cat}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Icon className="h-5 w-5" />
                {config.label}施設情報
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {cat === "pool" && <PoolInfo {...props} />}
              {cat === "court" && <CourtInfo {...props} />}
              {cat === "hall" && <HallInfo {...props} />}
              {cat === "field" && <FieldInfo {...props} />}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="flex justify-between border-b border-border/50 py-2 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

function PoolInfo({ poolLanes, poolLengthM, poolHeated }: CategoryInfoProps) {
  const hasData = poolLanes || poolLengthM || poolHeated !== undefined;
  if (!hasData) return <p className="text-sm text-muted-foreground">情報なし</p>;

  return (
    <div>
      <InfoRow label="レーン数" value={poolLanes ? `${poolLanes}レーン` : null} />
      <InfoRow label="長さ" value={poolLengthM ? `${poolLengthM}m` : null} />
      <InfoRow
        label="温水"
        value={
          poolHeated !== undefined && poolHeated !== null ? (poolHeated ? "あり" : "なし") : null
        }
      />
    </div>
  );
}

function CourtInfo({ courtType, courtCount, courtSurface, courtLighting }: CategoryInfoProps) {
  const hasData = courtType || courtCount || courtSurface || courtLighting !== undefined;
  if (!hasData) return <p className="text-sm text-muted-foreground">情報なし</p>;

  return (
    <div>
      <InfoRow label="コートタイプ" value={courtType} />
      <InfoRow label="面数" value={courtCount ? `${courtCount}面` : null} />
      <InfoRow label="表面" value={courtSurface} />
      <InfoRow
        label="照明"
        value={
          courtLighting !== undefined && courtLighting !== null
            ? courtLighting
              ? "あり"
              : "なし"
            : null
        }
      />
    </div>
  );
}

function HallInfo({ hallSports, hallAreaSqm }: CategoryInfoProps) {
  const hasData = (hallSports && hallSports.length > 0) || hallAreaSqm;
  if (!hasData) return <p className="text-sm text-muted-foreground">情報なし</p>;

  return (
    <div className="space-y-3">
      <InfoRow label="面積" value={hallAreaSqm ? `${hallAreaSqm}㎡` : null} />
      {hallSports && hallSports.length > 0 && (
        <div>
          <p className="text-sm text-muted-foreground mb-2">対応スポーツ</p>
          <div className="flex flex-wrap gap-2">
            {hallSports.map(sport => (
              <Badge key={sport} variant="outline">
                {sport}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function FieldInfo({ fieldType, fieldCount, fieldLighting }: CategoryInfoProps) {
  const hasData = fieldType || fieldCount || fieldLighting !== undefined;
  if (!hasData) return <p className="text-sm text-muted-foreground">情報なし</p>;

  return (
    <div>
      <InfoRow label="グラウンドタイプ" value={fieldType} />
      <InfoRow label="面数" value={fieldCount ? `${fieldCount}面` : null} />
      <InfoRow
        label="照明"
        value={
          fieldLighting !== undefined && fieldLighting !== null
            ? fieldLighting
              ? "あり"
              : "なし"
            : null
        }
      />
    </div>
  );
}
