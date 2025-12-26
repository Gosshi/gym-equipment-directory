"use client";

import { Map, List } from "lucide-react";
import { usePathname, useSearchParams } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function MobileViewToggle() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const isMap = pathname === "/map";

  // Existing query params are preserved
  const queryString = searchParams.toString();
  const targetPath = isMap ? "/search" : "/map";
  const href = queryString ? `${targetPath}?${queryString}` : targetPath;

  return (
    <div className="fixed bottom-6 left-0 right-0 z-50 flex justify-center lg:hidden pointer-events-none">
      <Button
        asChild
        className={cn(
          "rounded-full shadow-lg pointer-events-auto",
          "bg-foreground text-background hover:bg-foreground/90",
          "flex items-center gap-2 px-6 h-12",
        )}
      >
        <Link href={href}>
          {isMap ? (
            <>
              <List className="h-4 w-4" />
              <span>リストで表示</span>
            </>
          ) : (
            <>
              <Map className="h-4 w-4" />
              <span>地図で表示</span>
            </>
          )}
        </Link>
      </Button>
    </div>
  );
}
