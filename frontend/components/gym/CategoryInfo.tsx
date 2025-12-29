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
  // Archery
  archeryType?: string | null;
  archeryRooms?: number | null;

  // Meta
  facility_meta?: Record<string, unknown>;
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
  studio: { label: "スタジオ", icon: LayoutGrid },
  archery: { label: "弓道場", icon: LayoutGrid },
  martial_arts: { label: "武道場", icon: LayoutGrid },
};

// Helper to format keys like "2_hours" -> "2時間", "usage_fee" -> "利用料"
const formatKey = (key: string): string => {
  const normalized = key.replace(/_/g, " ");
  // Common mappings
  if (key === "usage_fee") return "利用料";
  if (key === "price") return "料金";
  if (key.endsWith("_hours") || key.endsWith("hours")) {
    return key.replace(/_?hours?$/i, "時間");
  }
  if (key === "full") return "全面";
  if (key === "half") return "半面";
  if (key === "1_4") return "1/4面";
  if (key === "open") return "開始";
  if (key === "close") return "終了";

  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
};

// Helper to format values like 6000 -> ¥6,000
const formatValue = (value: unknown): string => {
  if (typeof value === "number") {
    return `¥${value.toLocaleString()}`;
  }
  return String(value);
};

const extractMetaInfo = (
  meta: Record<string, unknown> | undefined,
  category: string,
  key: "fee" | "hours",
): string | null => {
  if (!meta) return null;

  // 1. Try direct category access: meta[category][key] (e.g. meta.pool.fee)
  const catObj = meta[category];
  if (catObj && typeof catObj === "object") {
    const val = (catObj as Record<string, unknown>)[key];
    if (typeof val === "string" || typeof val === "number") return String(val);
  }

  // 2. Try nested under key: meta[key][category] (e.g. meta.fee.court)
  const rootObj = meta[key];
  if (rootObj && typeof rootObj === "object") {
    const target = (rootObj as Record<string, unknown>)[category];

    // If it's a simple value
    if (typeof target === "string" || typeof target === "number") {
      return String(target);
    }

    // If it's an object, return JSON string for renderComplexValue
    if (target && typeof target === "object") {
      return JSON.stringify(target);
    }
  }

  return null;
};

const renderComplexValue = (value: string): React.ReactNode => {
  try {
    const parsed = JSON.parse(value);
    if (typeof parsed !== "object" || parsed === null) return value;

    // Recursive renderer
    const renderNode = (node: unknown, depth = 0): React.ReactNode => {
      if (typeof node !== "object" || node === null) return formatValue(node);

      return (
        <div className={`grid gap-1 ${depth > 0 ? "mt-1 pl-3 border-l-2 border-border/50" : ""}`}>
          {Object.entries(node).map(([k, v]) => (
            <div key={k} className="text-sm">
              <span className="font-medium text-muted-foreground mr-2">{formatKey(k)}:</span>
              <span className="text-foreground">
                {typeof v === "object" ? renderNode(v, depth + 1) : formatValue(v)}
              </span>
            </div>
          ))}
        </div>
      );
    };
    return renderNode(parsed);
  } catch {
    return value;
  }
};

export function CategoryInfo(props: CategoryInfoProps) {
  const { category, categories = [], facility_meta } = props;

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

        // Extract category-specific fees and hours
        const fee = extractMetaInfo(facility_meta, cat, "fee");
        const hours = extractMetaInfo(facility_meta, cat, "hours");

        return (
          <Card key={cat}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Icon className="h-5 w-5" />
                {config.label}施設情報
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {fee && <InfoRow label="料金" value={renderComplexValue(fee)} />}
              {hours && <InfoRow label="利用時間" value={renderComplexValue(hours)} />}

              {cat === "pool" && <PoolInfo {...props} />}
              {cat === "court" && <CourtInfo {...props} />}
              {cat === "hall" && <HallInfo {...props} />}
              {cat === "field" && <FieldInfo {...props} />}
              {cat === "archery" && <ArcheryInfo {...props} />}
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
    <div className="flex flex-col gap-1 border-b border-border/50 py-2 last:border-0 sm:flex-row sm:justify-between sm:gap-4">
      <span className="shrink-0 text-sm text-muted-foreground">{label}</span>
      <span className="text-right text-sm font-medium">{value}</span>
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

function ArcheryInfo({ archeryType, archeryRooms }: CategoryInfoProps) {
  const hasData = archeryType || archeryRooms;
  if (!hasData) return <p className="text-sm text-muted-foreground">情報なし</p>;

  return (
    <div>
      <InfoRow label="種類" value={archeryType} />
      <InfoRow label="道場数" value={archeryRooms ? `${archeryRooms}室` : null} />
    </div>
  );
}
