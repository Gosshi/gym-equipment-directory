"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { ApiError } from "@/lib/apiClient";
import { reportGym } from "@/services/reports";
import type { ReportGymType } from "@/types/api";

interface ReportGymFormProps {
  slug: string;
  gymName?: string;
}

type CategoryValue = "" | "equipment" | "address" | "hours" | "other";

const CATEGORY_OPTIONS: Array<{ value: CategoryValue; label: string }> = [
  { value: "", label: "選択しない (任意)" },
  { value: "equipment", label: "設備の情報が違う" },
  { value: "address", label: "住所・アクセスが違う" },
  { value: "hours", label: "営業時間が違う" },
  { value: "other", label: "その他" },
];

const MIN_MESSAGE_LENGTH = 5;

const resolveReportType = (category: CategoryValue): ReportGymType => {
  switch (category) {
    case "equipment":
    case "address":
    case "hours":
      return "wrong_info";
    case "other":
    default:
      return "other";
  }
};

const parseApiErrorMessage = (error: ApiError): string | null => {
  const raw = error.message?.trim();
  if (!raw) {
    return null;
  }

  if (raw.startsWith("{") || raw.startsWith("[")) {
    try {
      const data = JSON.parse(raw) as unknown;
      if (Array.isArray(data)) {
        const first = data[0] as Record<string, unknown> | string | undefined;
        if (!first) return null;
        if (typeof first === "string") return first;
        const msg = first.msg ?? first.message ?? first.detail;
        return typeof msg === "string" ? msg : null;
      }

      if (typeof data === "object" && data !== null) {
        const record = data as Record<string, unknown>;
        const detail = record.detail;
        if (typeof detail === "string") {
          return detail;
        }
        if (Array.isArray(detail)) {
          for (const item of detail) {
            if (!item) continue;
            if (typeof item === "string") {
              return item;
            }
            if (typeof item === "object") {
              const value =
                (item as Record<string, unknown>).msg ??
                (item as Record<string, unknown>).message ??
                (item as Record<string, unknown>).detail;
              if (typeof value === "string") {
                return value;
              }
            }
          }
        }
        const message = record.message;
        if (typeof message === "string") {
          return message;
        }
      }
    } catch {
      return raw;
    }
  }

  return raw;
};

const translateMessageError = (input: string | null): string | null => {
  if (!input) {
    return null;
  }
  if (input.toLowerCase().includes("at least")) {
    return "本文は5文字以上で入力してください";
  }
  return input;
};

export function ReportGymForm({ slug, gymName }: ReportGymFormProps) {
  const router = useRouter();
  const { toast } = useToast();

  const [message, setMessage] = useState("");
  const [category, setCategory] = useState<CategoryValue>("");
  const [messageError, setMessageError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleMessageChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    const { value } = event.target;
    setMessage(value);
    if (messageError && value.trim().length >= MIN_MESSAGE_LENGTH) {
      setMessageError(null);
    }
    if (formError) {
      setFormError(null);
    }
  };

  const handleCategoryChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const { value } = event.target;
    if (value === "equipment" || value === "address" || value === "hours" || value === "other") {
      setCategory(value);
    } else {
      setCategory("");
    }
    if (formError) {
      setFormError(null);
    }
  };

  const handleCancel = () => {
    if (isSubmitting) {
      return;
    }
    router.push(`/gyms/${encodeURIComponent(slug)}`);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }

    setFormError(null);

    const trimmedMessage = message.trim();
    if (trimmedMessage.length < MIN_MESSAGE_LENGTH) {
      setMessageError("本文は5文字以上で入力してください");
      return;
    }
    setMessageError(null);

    setIsSubmitting(true);
    try {
      await reportGym(slug, {
        type: resolveReportType(category),
        message: trimmedMessage,
      });

      toast({
        title: "報告ありがとうございます",
        description: "いただいた内容を確認し、順次対応いたします。",
      });
      router.replace(`/gyms/${encodeURIComponent(slug)}`);
    } catch (error) {
      if (error instanceof ApiError) {
        const parsedMessage = translateMessageError(parseApiErrorMessage(error));
        if (error.status && error.status >= 500) {
          toast({
            variant: "destructive",
            title: "送信に失敗しました",
            description: parsedMessage ?? "時間をおいて再度お試しください。",
          });
        } else {
          if (error.status === 422 && parsedMessage) {
            setMessageError(parsedMessage);
          }
          setFormError(parsedMessage ?? "送信に失敗しました。入力内容をご確認ください。");
        }
      } else {
        const fallback = error instanceof Error ? error.message : "送信に失敗しました";
        setFormError(fallback);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-10 sm:py-12">
      <div className="space-y-8">
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">問題を報告</h1>
          {gymName ? (
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{gymName}</span> に関する更新内容をお知らせください。
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">ジムの情報に誤りがありましたら以下からご連絡ください。</p>
          )}
        </header>

        <form className="space-y-6" onSubmit={handleSubmit} noValidate>
          <div className="space-y-2">
            <label className="block text-sm font-medium text-foreground" htmlFor="report-message">
              本文 <span className="text-destructive">*</span>
            </label>
            <textarea
              id="report-message"
              name="message"
              value={message}
              onChange={handleMessageChange}
              required
              minLength={MIN_MESSAGE_LENGTH}
              rows={6}
              aria-invalid={messageError ? "true" : "false"}
              aria-describedby={messageError ? "report-message-error" : undefined}
              className="min-h-[160px] w-full resize-vertical rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-0"
              placeholder="気付いた点や詳細をできるだけ具体的にご入力ください"
            />
            {messageError ? (
              <p id="report-message-error" className="text-sm text-destructive">
                {messageError}
              </p>
            ) : null}
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-foreground" htmlFor="report-category">
              カテゴリ
            </label>
            <select
              id="report-category"
              name="category"
              value={category}
              onChange={handleCategoryChange}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-0"
            >
              {CATEGORY_OPTIONS.map((option) => (
                <option key={option.value || "none"} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {formError ? (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {formError}
            </div>
          ) : null}

          <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
            <Button type="submit" disabled={isSubmitting} className="sm:min-w-[120px]">
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                  送信中...
                </>
              ) : (
                "送信"
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              disabled={isSubmitting}
              className="sm:min-w-[120px]"
            >
              キャンセル
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
