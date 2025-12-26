"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, Home } from "lucide-react";
import { Fragment, useMemo } from "react";

import { cn } from "@/lib/utils";

interface BreadcrumbItem {
  label: string;
  href: string;
  current?: boolean;
}

interface BreadcrumbsProps {
  items?: BreadcrumbItem[];
  className?: string;
}

const pathLabels: Record<string, string> = {
  gyms: "ジム検索",
  nearby: "現在地から探す",
  map: "地図",
  search: "検索",
  me: "マイページ",
  favorites: "お気に入り",
  admin: "管理者",
  candidates: "候補一覧",
  terms: "利用規約",
  privacy: "プライバシーポリシー",
  contact: "お問い合わせ",
};

export function Breadcrumbs({ items, className }: BreadcrumbsProps) {
  const pathname = usePathname();

  const autoItems = useMemo(() => {
    if (items) return items;

    const segments = pathname.split("/").filter(Boolean);
    const breadcrumbItems: BreadcrumbItem[] = [];

    segments.forEach((segment, index) => {
      // Skip dynamic segments (usually slugs) or very long names
      const isSlug = segment.length > 20 || segment.includes("-");

      const href = "/" + segments.slice(0, index + 1).join("/");
      const label = pathLabels[segment] || (isSlug ? null : segment);

      if (label) {
        breadcrumbItems.push({
          label,
          href,
          current: index === segments.length - 1,
        });
      }
    });

    return breadcrumbItems;
  }, [pathname, items]);

  // Don't render if only home or no items
  if (autoItems.length === 0) {
    return null;
  }

  return (
    <nav
      aria-label="パンくずリスト"
      className={cn("flex items-center gap-1 font-mono text-xs", className)}
    >
      {/* Home Link */}
      <Link
        href="/"
        className="flex items-center gap-1 text-muted-foreground transition-colors hover:text-foreground"
        aria-label="ホーム"
      >
        <Home className="h-3 w-3" />
        <span className="hidden sm:inline uppercase tracking-widest">HOME</span>
      </Link>

      {/* Breadcrumb Items */}
      {autoItems.map((item, index) => (
        <Fragment key={item.href}>
          <ChevronRight aria-hidden="true" className="h-3 w-3 text-muted-foreground/50" />
          {item.current ? (
            <span
              aria-current="page"
              className="font-bold uppercase tracking-widest text-foreground"
            >
              {item.label}
            </span>
          ) : (
            <Link
              href={item.href}
              className="uppercase tracking-widest text-muted-foreground transition-colors hover:text-foreground"
            >
              {item.label}
            </Link>
          )}
        </Fragment>
      ))}
    </nav>
  );
}
