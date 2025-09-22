import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface GymMapPlaceholderProps {
  address?: string;
}

export function GymMapPlaceholder({ address }: GymMapPlaceholderProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>アクセス</CardTitle>
        <CardDescription>地図連携は今後のアップデートで提供予定です。</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex h-48 w-full flex-col items-center justify-center gap-2 rounded-md border border-dashed border-muted-foreground/50 bg-muted/30 text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Map Placeholder</span>
          <p className="text-center text-xs text-muted-foreground">
            現在は地図の準備中です。正式な地図連携に向けて開発を進めています。
          </p>
          {address ? <p className="text-center text-xs text-muted-foreground">最寄り住所: {address}</p> : null}
        </div>
      </CardContent>
    </Card>
  );
}
