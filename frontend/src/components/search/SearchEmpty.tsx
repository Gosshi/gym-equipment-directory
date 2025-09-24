import { Compass } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type SearchEmptyProps = {
  onResetFilters?: () => void;
  className?: string;
};

export function SearchEmpty({ onResetFilters, className }: SearchEmptyProps) {
  return (
    <div
      aria-live="polite"
      className={cn(
        "flex flex-col items-center gap-5 rounded-2xl border border-dashed",
        "border-muted-foreground/40 bg-muted/20 p-8 text-center shadow-sm sm:p-10",
        "max-w-2xl mx-auto",
        className,
      )}
      role="status"
    >
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-background shadow">
        <Compass aria-hidden="true" className="h-7 w-7 text-muted-foreground" />
      </div>
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">該当するジムが見つかりませんでした</h3>
        <p className="text-sm text-muted-foreground">
          条件を少し緩めるか、別のキーワードでお試しください。
        </p>
      </div>
      <ul className="list-disc space-y-1 text-left text-sm text-muted-foreground">
        <li>キーワードを短くするか、別の言葉を試す</li>
        <li>距離やカテゴリの条件を広げて再検索する</li>
        <li>都道府県・市区町村の指定を解除する</li>
      </ul>
      {onResetFilters ? (
        <Button onClick={onResetFilters} type="button" variant="outline">
          条件をクリア
        </Button>
      ) : null}
    </div>
  );
}
