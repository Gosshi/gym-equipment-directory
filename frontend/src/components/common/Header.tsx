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
        className="h-8 w-8 rounded-none border border-border object-cover"
        decoding="async"
        loading="lazy"
        src={user.avatarUrl}
      />
    );
  }

  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-none border border-border bg-muted text-sm font-bold text-muted-foreground">
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
        title: "LOGGED OUT",
        description: "See you at the gym.",
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Logout failed";
      toast({
        title: "ERROR",
        description: message,
        variant: "destructive",
      });
    }
  }, [signOut]);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-8">
          <Link className="flex items-center gap-2" href="/">
            <span className="font-heading text-2xl font-black uppercase tracking-tighter text-foreground">
              IRON <span className="text-accent">MAP</span>
            </span>
          </Link>
          <nav className="hidden items-center gap-6 sm:flex">
            <Link
              className="font-mono text-xs font-bold uppercase tracking-widest text-muted-foreground transition-colors hover:text-accent"
              href="/gyms"
            >
              Search
            </Link>
            <Link
              className="font-mono text-xs font-bold uppercase tracking-widest text-muted-foreground transition-colors hover:text-accent"
              href="/gyms/nearby"
            >
              Nearby
            </Link>
            <Link
              className="font-mono text-xs font-bold uppercase tracking-widest text-muted-foreground transition-colors hover:text-accent"
              href="/me/favorites"
            >
              Favorites
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-4">
          {status === "loading" ? (
            <div className="flex items-center gap-2">
              <Skeleton className="h-8 w-8 rounded-none" />
              <Skeleton className="h-4 w-24" />
            </div>
          ) : null}
          {status !== "loading" && !user ? (
            <Button
              onClick={handleLoginClick}
              type="button"
              variant="outline"
              className="rounded-none border-accent font-mono text-xs font-bold uppercase tracking-wider text-accent hover:bg-accent hover:text-accent-foreground"
            >
              Login
            </Button>
          ) : null}
          {status !== "loading" && user ? (
            <div className="relative" ref={menuRef}>
              <button
                aria-expanded={menuOpen}
                className={cn(
                  "flex items-center gap-3 rounded-none border border-transparent px-2 py-1 transition hover:bg-accent/10",
                  menuOpen && "border-border bg-accent/10",
                )}
                onClick={() => setMenuOpen(prev => !prev)}
                type="button"
              >
                <UserAvatar user={user} />
                <span className="hidden font-mono text-xs font-bold uppercase tracking-wider text-foreground sm:inline">
                  {user.name}
                </span>
              </button>
              {menuOpen ? (
                <div className="absolute right-0 mt-2 w-48 border border-border bg-card p-1 shadow-xl">
                  <Link
                    className="block px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-foreground transition hover:bg-accent hover:text-accent-foreground"
                    href="/me/favorites"
                    onClick={() => setMenuOpen(false)}
                  >
                    Favorites
                  </Link>
                  <button
                    className="block w-full px-4 py-2 text-left font-mono text-xs font-bold uppercase tracking-wider text-foreground transition hover:bg-destructive hover:text-destructive-foreground"
                    onClick={handleSignOut}
                    type="button"
                  >
                    Logout
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
