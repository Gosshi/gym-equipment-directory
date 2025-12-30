import { AlertTriangle, RotateCcw } from "lucide-react";

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
        "flex flex-col items-center gap-6 border-2 border-dashed",
        "border-muted-foreground/30 bg-muted/10 p-8 text-center sm:p-12",
        "max-w-2xl mx-auto",
        className,
      )}
      role="status"
    >
      {/* Status Badge */}
      <div className="flex items-center gap-2 border border-muted-foreground/30 bg-background px-4 py-2">
        <AlertTriangle aria-hidden="true" className="h-4 w-4 text-muted-foreground" />
        <span className="font-mono text-xs font-bold uppercase tracking-widest text-muted-foreground">
          NO RESULTS FOUND
        </span>
      </div>

      {/* Main Message */}
      <div className="space-y-3">
        <h3 className="font-heading text-2xl font-bold uppercase tracking-tight sm:text-3xl">
          該当する施設が見つかりませんでした
        </h3>
        <p className="font-mono text-sm text-muted-foreground">
          条件を緩めるか、別のキーワードで検索してください
        </p>
      </div>

      {/* Suggestions */}
      <div className="w-full max-w-md space-y-2 text-left">
        <p className="font-mono text-xs font-bold uppercase tracking-widest text-muted-foreground/70">
          SUGGESTIONS:
        </p>
        <ul className="space-y-1 font-mono text-xs text-muted-foreground">
          <li className="flex items-center gap-2">
            <span className="h-1 w-1 bg-muted-foreground" />
            キーワードを短くするか、別の言葉を試す
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1 w-1 bg-muted-foreground" />
            距離やカテゴリの条件を広げて再検索する
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1 w-1 bg-muted-foreground" />
            都道府県・市区町村の指定を解除する
          </li>
        </ul>
      </div>

      {/* Reset Button */}
      {onResetFilters ? (
        <Button
          onClick={onResetFilters}
          type="button"
          variant="outline"
          className="gap-2 font-mono text-xs font-bold uppercase tracking-widest"
        >
          <RotateCcw className="h-3 w-3" />
          条件をクリア
        </Button>
      ) : null}
    </div>
  );
}
