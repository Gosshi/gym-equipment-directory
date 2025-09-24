import { AlertCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type SearchErrorProps = {
  message?: string | null;
  onRetry: () => void;
  className?: string;
};

const DEFAULT_ERROR_MESSAGE = "ジムの取得に失敗しました";

export function SearchError({ message, onRetry, className }: SearchErrorProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-4 rounded-lg border border-destructive/40",
        "bg-destructive/10 p-6 text-center text-sm text-destructive",
        className,
      )}
      role="alert"
    >
      <div className="flex items-start gap-2">
        <AlertCircle aria-hidden="true" className="mt-0.5 h-5 w-5" />
        <p className="text-left">{message || DEFAULT_ERROR_MESSAGE}</p>
      </div>
      <Button onClick={onRetry} type="button" variant="outline">
        再試行
      </Button>
    </div>
  );
}
