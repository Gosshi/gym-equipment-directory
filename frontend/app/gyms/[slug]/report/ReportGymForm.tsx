"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import { ApiError } from "@/lib/apiClient";
import { reportGymIssue } from "@/services/reports";

const REASON_VALUES = ["hours", "equipment", "address", "closed", "other"] as const;

const REASON_OPTIONS = [
  { value: REASON_VALUES[0], label: "営業時間の誤り" },
  { value: REASON_VALUES[1], label: "設備の誤り" },
  { value: REASON_VALUES[2], label: "住所・地図の誤り" },
  { value: REASON_VALUES[3], label: "閉業している" },
  { value: REASON_VALUES[4], label: "その他" },
] as const;

type ReasonOptionValue = (typeof REASON_VALUES)[number];

const contactSchema = z
  .string()
  .trim()
  .max(320, { message: "メールアドレスは320文字以内で入力してください。" })
  .email({ message: "有効なメールアドレスを入力してください。" });

export const reportGymIssueSchema = z.object({
  reason: z.enum(REASON_VALUES, { message: "理由を選択してください。" }),
  details: z
    .string({ message: "詳細を入力してください。" })
    .trim()
    .min(20, { message: "詳細は20文字以上で入力してください。" })
    .max(1000, { message: "詳細は1000文字以内で入力してください。" }),
  contact: z.union([contactSchema, z.literal("")]).optional(),
});

export type ReportGymIssueInput = z.infer<typeof reportGymIssueSchema>;

interface ReportGymFormProps {
  slug: string;
  gymName?: string;
}

type ReportGymIssueField = keyof ReportGymIssueInput;

type ParsedError = {
  message?: string;
  fieldErrors: Partial<Record<ReportGymIssueField, string>>;
};

const FORM_FIELD_NAMES: ReportGymIssueField[] = ["reason", "details", "contact"];
const FIELD_NAME_SET = new Set<ReportGymIssueField>(FORM_FIELD_NAMES);

const formatStatusMessage = (status: number | undefined, message: string) =>
  status ? `HTTP ${status}: ${message}` : message;

const extractFieldNameFromLoc = (loc: unknown): ReportGymIssueField | undefined => {
  if (!Array.isArray(loc)) {
    return undefined;
  }
  for (let index = loc.length - 1; index >= 0; index -= 1) {
    const value = loc[index];
    if (typeof value === "string" && FIELD_NAME_SET.has(value as ReportGymIssueField)) {
      return value as ReportGymIssueField;
    }
  }
  return undefined;
};

const parseApiError = (error: ApiError): ParsedError => {
  const fieldErrors: ParsedError["fieldErrors"] = {};
  const messages: string[] = [];
  const rawMessage = error.message?.trim();

  const appendMessage = (message: unknown, field?: ReportGymIssueField) => {
    if (typeof message !== "string" || message.trim().length === 0) {
      return;
    }
    if (field && FIELD_NAME_SET.has(field)) {
      if (!fieldErrors[field]) {
        fieldErrors[field] = message;
      }
      return;
    }
    messages.push(message);
  };

  const visit = (value: unknown, hint?: ReportGymIssueField) => {
    if (!value) {
      return;
    }
    if (typeof value === "string") {
      appendMessage(value, hint);
      return;
    }
    if (Array.isArray(value)) {
      value.forEach(item => visit(item, hint));
      return;
    }
    if (typeof value === "object") {
      const record = value as Record<string, unknown>;
      const fieldFromLoc = extractFieldNameFromLoc(record.loc);
      const fieldName = ((): ReportGymIssueField | undefined => {
        const directField = record.field ?? record.name ?? record.param ?? record.path;
        if (
          typeof directField === "string" &&
          FIELD_NAME_SET.has(directField as ReportGymIssueField)
        ) {
          return directField as ReportGymIssueField;
        }
        if (fieldFromLoc) {
          return fieldFromLoc;
        }
        if (hint && FIELD_NAME_SET.has(hint)) {
          return hint;
        }
        return undefined;
      })();

      const messageCandidate =
        (typeof record.message === "string" && record.message) ||
        (typeof record.msg === "string" && record.msg) ||
        (typeof record.detail === "string" && record.detail) ||
        (typeof record.error === "string" && record.error) ||
        (typeof record.description === "string" && record.description);

      if (messageCandidate) {
        appendMessage(messageCandidate, fieldName);
      }

      const nestedErrors = record.errors;
      if (nestedErrors && typeof nestedErrors === "object") {
        Object.entries(nestedErrors as Record<string, unknown>).forEach(([key, nested]) => {
          visit(
            nested,
            FIELD_NAME_SET.has(key as ReportGymIssueField) ? (key as ReportGymIssueField) : hint,
          );
        });
      }

      const detailValue = record.detail;
      if (detailValue && typeof detailValue !== "string") {
        visit(detailValue, fieldName ?? hint);
      }

      const detailsValue = record.details;
      if (detailsValue && typeof detailsValue !== "string") {
        visit(detailsValue, fieldName ?? hint);
      }

      for (const [key, nested] of Object.entries(record)) {
        if (
          [
            "field",
            "name",
            "param",
            "path",
            "loc",
            "msg",
            "message",
            "detail",
            "error",
            "description",
            "errors",
            "details",
          ].includes(key)
        ) {
          continue;
        }
        visit(nested, hint);
      }
    }
  };

  if (rawMessage) {
    const firstChar = rawMessage[0];
    if (firstChar === "{" || firstChar === "[") {
      try {
        const data = JSON.parse(rawMessage) as unknown;
        visit(data);
      } catch {
        messages.push(rawMessage);
      }
    } else {
      messages.push(rawMessage);
    }
  }

  return {
    fieldErrors,
    message: messages.find(item => item.trim().length > 0),
  };
};

export function ReportGymForm({ slug, gymName }: ReportGymFormProps) {
  const router = useRouter();
  const { toast } = useToast();

  const defaultValues = useMemo<Partial<ReportGymIssueInput>>(
    () => ({ details: "", contact: "" }),
    [],
  );

  const form = useForm<ReportGymIssueInput>({
    resolver: zodResolver(reportGymIssueSchema),
    defaultValues,
    mode: "onSubmit",
  });

  const {
    handleSubmit,
    control,
    formState: { isSubmitting, errors },
    setError,
    clearErrors,
    getValues,
  } = form;

  const onSubmit = async (values: ReportGymIssueInput) => {
    clearErrors();
    try {
      const contactValue =
        typeof values.contact === "string" && values.contact.trim().length > 0
          ? values.contact.trim()
          : undefined;

      await reportGymIssue(slug, {
        reason: values.reason,
        details: values.details.trim(),
        contact: contactValue,
      });
      toast({
        title: "報告を受け付けました",
        description: "ご協力ありがとうございます。内容を確認いたします。",
      });
      router.replace(`/gyms/${slug}`);
    } catch (error) {
      if (error instanceof ApiError) {
        const parsed = parseApiError(error);

        if (error.status && error.status >= 500) {
          const message =
            parsed.message ?? "サーバーエラーが発生しました。時間をおいて再度お試しください。";
          toast({
            variant: "destructive",
            title: "送信に失敗しました",
            description: formatStatusMessage(error.status, message),
          });
          setError("root", { type: "server", message: formatStatusMessage(error.status, message) });
          return;
        }

        let hasFieldError = false;
        for (const [field, message] of Object.entries(parsed.fieldErrors)) {
          if (!message) {
            continue;
          }
          const fieldName = field as ReportGymIssueField;
          if (FIELD_NAME_SET.has(fieldName) && fieldName in getValues()) {
            setError(fieldName, { type: "server", message });
            hasFieldError = true;
          }
        }

        if (parsed.message) {
          setError("root", {
            type: "server",
            message: formatStatusMessage(error.status, parsed.message),
          });
        } else if (!hasFieldError) {
          const fallback =
            error.status === 400 || error.status === 422
              ? "送信に失敗しました。入力内容をご確認ください。"
              : "送信に失敗しました。時間をおいて再度お試しください。";
          setError("root", {
            type: "server",
            message: formatStatusMessage(error.status, fallback),
          });
        }
      } else {
        const message = error instanceof Error ? error.message : "送信に失敗しました。";
        setError("root", { type: "server", message });
      }
    }
  };

  const rootError = errors.root?.message;

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-10 sm:py-12">
      <div className="space-y-8">
        <div className="space-y-2">
          <Link
            href={`/gyms/${slug}`}
            className="inline-flex items-center text-sm font-medium text-muted-foreground hover:text-foreground"
            aria-label="ジム詳細ページへ戻る"
          >
            ← 詳細へ戻る
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight">問題を報告</h1>
          {gymName ? (
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{gymName}</span>{" "}
              に関する誤りや更新情報をご連絡ください。
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              掲載内容に誤りがある場合は、以下のフォームからお知らせください。
            </p>
          )}
        </div>

        <Form {...form}>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
            <FormField
              control={control}
              name="reason"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    理由 <span className="text-destructive">*</span>
                  </FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger aria-label="誤りの理由を選択" aria-required="true">
                        <SelectValue placeholder="理由を選択してください" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {REASON_OPTIONS.map(option => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={control}
              name="details"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    詳細 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Textarea
                      {...field}
                      value={field.value ?? ""}
                      aria-label="報告内容の詳細"
                      aria-required="true"
                      minLength={20}
                      maxLength={1000}
                      rows={8}
                      placeholder="気付いた点や誤りの内容をできるだけ詳しくご記入ください"
                      className="min-h-[180px]"
                    />
                  </FormControl>
                  <FormDescription>20〜1000文字でご入力ください。</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={control}
              name="contact"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>ご連絡先（任意）</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      value={field.value ?? ""}
                      type="email"
                      inputMode="email"
                      autoComplete="email"
                      aria-label="ご連絡先メールアドレス"
                      placeholder="確認のご連絡が必要な場合はメールアドレスをご入力ください"
                    />
                  </FormControl>
                  <FormDescription>必要に応じて運営からご連絡する場合があります。</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {rootError ? (
              <Alert variant="destructive">
                <AlertTitle>送信エラー</AlertTitle>
                <AlertDescription>{rootError}</AlertDescription>
              </Alert>
            ) : null}

            <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
              <Button type="submit" disabled={isSubmitting} className="sm:min-w-[140px]">
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                    送信中...
                  </>
                ) : (
                  "送信する"
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.replace(`/gyms/${encodeURIComponent(slug)}`)}
                disabled={isSubmitting}
                className="sm:min-w-[140px]"
              >
                キャンセル
              </Button>
            </div>
          </form>
        </Form>
      </div>
    </div>
  );
}
