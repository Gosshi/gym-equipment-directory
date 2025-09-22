"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

import { useAuth } from "@/auth/AuthProvider";
import type { User } from "@/types/user";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { toast } from "@/components/ui/use-toast";

const getInitials = (name: string) => {
  const trimmed = name.trim();
  if (!trimmed) {
    return "?";
  }
  const parts = trimmed.split(/\s+/).filter(Boolean);
  if (parts.length === 1) {
    return parts[0]!.charAt(0).toUpperCase();
  }
  return `${parts[0]!.charAt(0)}${parts[parts.length - 1]!.charAt(0)}`.toUpperCase();
};

const UserAvatar = ({ user }: { user: User }) => {
  if (user.avatarUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        alt={`${user.name} のアバター`}
        className="h-8 w-8 rounded-full object-cover"
        src={user.avatarUrl}
      />
    );
  }

  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-sm font-medium text-muted-foreground">
      {getInitials(user.name)}
    </div>
  );
};

export function AppHeader() {
  const { user, status, openLoginDialog, signOut } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menuOpen) {
      return;
    }

    const handleClickOutside = (event: MouseEvent) => {
      if (!menuRef.current) {
        return;
      }
      if (!menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [menuOpen]);

  useEffect(() => {
    if (!user) {
      setMenuOpen(false);
    }
  }, [user]);

  const handleLoginClick = useCallback(() => {
    openLoginDialog();
  }, [openLoginDialog]);

  const handleSignOut = useCallback(async () => {
    try {
      await signOut();
      toast({
        title: "ログアウトしました",
        description: "またのご利用をお待ちしています。",
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "ログアウトに失敗しました";
      toast({
        title: "ログアウトに失敗しました",
        description: message,
        variant: "destructive",
      });
    }
  }, [signOut]);

  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-background/90 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4">
        <div className="flex items-center gap-6">
          <Link className="text-lg font-semibold text-foreground" href="/">
            Gym Equipment Directory
          </Link>
          <nav className="hidden items-center gap-4 text-sm font-medium text-muted-foreground sm:flex">
            <Link className="transition hover:text-foreground" href="/gyms">
              ジム検索
            </Link>
            <Link className="transition hover:text-foreground" href="/me/favorites">
              お気に入り
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-3">
          {status === "loading" ? (
            <div className="flex items-center gap-2">
              <Skeleton className="h-8 w-8 rounded-full" />
              <Skeleton className="h-4 w-24" />
            </div>
          ) : null}
          {status !== "loading" && !user ? (
            <Button onClick={handleLoginClick} type="button">
              ログイン
            </Button>
          ) : null}
          {status !== "loading" && user ? (
            <div className="relative" ref={menuRef}>
              <button
                aria-expanded={menuOpen}
                className={cn(
                  "flex items-center gap-2 rounded-full border border-transparent px-2 py-1 text-sm transition",
                  menuOpen ? "border-border bg-muted" : "hover:bg-muted",
                )}
                onClick={() => setMenuOpen((prev) => !prev)}
                type="button"
              >
                <UserAvatar user={user} />
                <span className="hidden text-sm font-medium text-foreground sm:inline">{user.name}</span>
              </button>
              {menuOpen ? (
                <div className="absolute right-0 mt-2 w-48 rounded-md border border-border bg-popover p-2 shadow-lg">
                  <Link
                    className="block rounded-md px-3 py-2 text-sm text-foreground transition hover:bg-muted"
                    href="/me/favorites"
                    onClick={() => setMenuOpen(false)}
                  >
                    お気に入り
                  </Link>
                  <button
                    className="block w-full rounded-md px-3 py-2 text-left text-sm text-foreground transition hover:bg-muted"
                    onClick={handleSignOut}
                    type="button"
                  >
                    ログアウト
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
