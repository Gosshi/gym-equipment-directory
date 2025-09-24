"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import type { AuthStatus } from "@/auth/AuthProvider";
import type { AuthMode } from "@/auth/authClient";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface LoginDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSignIn: (nickname: string) => Promise<void> | void;
  isSubmitting: boolean;
  errorMessage: string | null;
  status: AuthStatus;
  mode: AuthMode;
}

export function LoginDialog({
  open,
  onOpenChange,
  onSignIn,
  isSubmitting,
  errorMessage,
  status,
  mode,
}: LoginDialogProps) {
  const [nickname, setNickname] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open) {
      setNickname("");
      setLocalError(null);
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onOpenChange(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    const focusTimeout = window.setTimeout(() => {
      inputRef.current?.focus();
    }, 20);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
      window.clearTimeout(focusTimeout);
    };
  }, [onOpenChange, open]);

  useEffect(() => {
    if (errorMessage) {
      setLocalError(errorMessage);
    }
  }, [errorMessage]);

  if (!open) {
    return null;
  }

  const handleSubmit: React.FormEventHandler<HTMLFormElement> = async event => {
    event.preventDefault();
    const trimmed = nickname.trim();
    if (!trimmed) {
      setLocalError("ニックネームを入力してください。");
      return;
    }

    setLocalError(null);
    await onSignIn(trimmed);
  };

  const handleBackdropClick: React.MouseEventHandler<HTMLDivElement> = event => {
    if (event.target === event.currentTarget) {
      onOpenChange(false);
    }
  };

  const description =
    mode === "stub"
      ? "ニックネームを入力するとスタブユーザーとしてサインインできます。"
      : "OAuth 認証でサインインします。";

  return createPortal(
    <div
      aria-hidden={!open}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 py-6"
      onClick={handleBackdropClick}
    >
      <div
        aria-modal
        className="w-full max-w-sm rounded-lg bg-background p-6 shadow-lg"
        role="dialog"
      >
        <div className="space-y-1">
          <h2 className="text-xl font-semibold">ログイン</h2>
          <p className="text-sm text-muted-foreground">{description}</p>
          {status === "loading" ? (
            <p className="text-xs text-muted-foreground">認証情報を確認しています...</p>
          ) : null}
        </div>
        <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground" htmlFor="login-nickname">
              ニックネーム
            </label>
            <input
              ref={inputRef}
              autoComplete="nickname"
              className={cn(
                "h-10 w-full rounded-md border border-input bg-background px-3 text-sm",
                "shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              )}
              disabled={isSubmitting}
              id="login-nickname"
              onChange={event => setNickname(event.target.value)}
              value={nickname}
            />
          </div>
          {localError ? <p className="text-sm text-destructive">{localError}</p> : null}
          <div className="flex items-center justify-end gap-2">
            <Button onClick={() => onOpenChange(false)} type="button" variant="outline">
              キャンセル
            </Button>
            <Button disabled={isSubmitting} type="submit">
              {isSubmitting ? "サインイン中..." : "サインイン"}
            </Button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
}
