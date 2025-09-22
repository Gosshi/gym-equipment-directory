"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, getApiBaseUrl } from "@/lib/api/client";
import { fetchHealth, type HealthResponse } from "@/lib/api/health";

interface HealthState {
  status: "idle" | "loading" | "success" | "error";
  data?: HealthResponse;
  checkedAt?: Date;
  errorMessage?: string;
}

const initialState: HealthState = {
  status: "idle",
};

const formatTimestamp = (date: Date) =>
  date.toLocaleString("ja-JP", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

export function HealthCheckCard() {
  const [state, setState] = useState<HealthState>(initialState);
  const apiConfig = useMemo(() => {
    try {
      return { baseUrl: getApiBaseUrl() };
    } catch (error) {
      const message = error instanceof Error ? error.message : "無効な API ベース URL です";
      return { error: message };
    }
  }, []);

  const runHealthCheck = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const data = await fetchHealth();
      setState({ status: "success", data, checkedAt: new Date() });
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "予期しないエラーが発生しました";
      setState({ status: "error", errorMessage: message });
    }
  }, []);

  useEffect(() => {
    if (!apiConfig.error) {
      void runHealthCheck();
    }
  }, [apiConfig.error, runHealthCheck]);

  if (apiConfig.error) {
    return (
      <Card className="max-w-md border-destructive/40">
        <CardHeader>
          <CardTitle>API 設定エラー</CardTitle>
          <CardDescription>環境変数を確認してください。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-start gap-3 text-destructive">
            <AlertCircle className="mt-1 h-5 w-5" aria-hidden="true" />
            <p className="text-sm">{apiConfig.error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const baseUrl = apiConfig.baseUrl;

  let content = null;
  switch (state.status) {
    case "loading":
      content = (
        <div className="space-y-4">
          <div className="flex items-center gap-3 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
            <span>ヘルスチェックを実行中です…</span>
          </div>
          <Skeleton className="h-12 w-full" />
        </div>
      );
      break;
    case "success": {
      const isHealthy = state.data?.status === "ok";
      content = (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <CheckCircle2
              className={isHealthy ? "h-6 w-6 text-emerald-500" : "h-6 w-6 text-amber-500"}
              aria-hidden="true"
            />
            <div>
              <p className="text-lg font-semibold">
                {isHealthy ? "API は正常に応答しています" : "API はエラーを返しました"}
              </p>
              <p className="text-sm text-muted-foreground">
                ベース URL: <span className="font-mono">{baseUrl}</span>
              </p>
            </div>
          </div>
          {state.data?.details && (
            <pre className="max-h-48 overflow-auto rounded-md border bg-muted/40 p-3 text-sm">
              {JSON.stringify(state.data.details, null, 2)}
            </pre>
          )}
        </div>
      );
      break;
    }
    case "error":
      content = (
        <div className="space-y-4">
          <div className="flex items-start gap-3 text-destructive">
            <AlertCircle className="mt-1 h-5 w-5" aria-hidden="true" />
            <div>
              <p className="text-lg font-semibold">ヘルスチェックに失敗しました</p>
              <p className="text-sm text-destructive/80">{state.errorMessage}</p>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            ベース URL: <span className="font-mono">{baseUrl}</span>
          </p>
        </div>
      );
      break;
    default:
      content = null;
  }

  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle>Gym Equipment API ヘルスチェック</CardTitle>
        <CardDescription>API の稼働状態を確認できます。</CardDescription>
      </CardHeader>
      <CardContent>{content}</CardContent>
      <CardFooter className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <Button
          onClick={runHealthCheck}
          disabled={state.status === "loading"}
          variant="secondary"
          className="w-full sm:w-auto"
        >
          {state.status === "loading" ? (
            <span className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              チェック中
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <RefreshCcw className="h-4 w-4" aria-hidden="true" />
              再チェック
            </span>
          )}
        </Button>
        {state.checkedAt && (
          <p className="text-xs text-muted-foreground">
            最終チェック: {formatTimestamp(state.checkedAt)}
          </p>
        )}
      </CardFooter>
    </Card>
  );
}
