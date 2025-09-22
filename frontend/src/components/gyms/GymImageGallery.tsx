"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, ImageOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface GymImageGalleryProps {
  images?: string[];
  name: string;
  className?: string;
}

export function GymImageGallery({ images, name, className }: GymImageGalleryProps) {
  const sanitized = useMemo(
    () => (images ?? []).filter((item): item is string => typeof item === "string" && item.length > 0),
    [images],
  );
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    setActiveIndex(0);
  }, [sanitized.length]);

  if (sanitized.length === 0) {
    return (
      <div
        className={cn(
          "flex aspect-[16/9] w-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-muted-foreground/40 bg-muted/50 text-sm text-muted-foreground",
          className,
        )}
      >
        <ImageOff aria-hidden className="h-8 w-8" />
        <p>表示可能な画像がまだ登録されていません。</p>
      </div>
    );
  }

  const goTo = (index: number) => {
    setActiveIndex((prev) => {
      if (index < 0) {
        return sanitized.length - 1;
      }
      if (index >= sanitized.length) {
        return 0;
      }
      return index;
    });
  };

  const goPrev = () => goTo(activeIndex - 1);
  const goNext = () => goTo(activeIndex + 1);

  return (
    <div className={cn("space-y-3", className)}>
      <div className="relative aspect-[16/9] w-full overflow-hidden rounded-lg bg-black/5">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          alt={`${name} のギャラリー画像 ${activeIndex + 1}`}
          className="h-full w-full object-cover"
          src={sanitized[activeIndex]}
        />
        {sanitized.length > 1 ? (
          <>
            <Button
              aria-label="前の画像"
              className="absolute left-3 top-1/2 -translate-y-1/2 rounded-full bg-background/70 shadow-sm hover:bg-background"
              onClick={goPrev}
              size="icon"
              type="button"
              variant="outline"
            >
              <ChevronLeft aria-hidden className="h-4 w-4" />
            </Button>
            <Button
              aria-label="次の画像"
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full bg-background/70 shadow-sm hover:bg-background"
              onClick={goNext}
              size="icon"
              type="button"
              variant="outline"
            >
              <ChevronRight aria-hidden className="h-4 w-4" />
            </Button>
            <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-2">
              {sanitized.map((_, index) => (
                <button
                  key={`${sanitized[index]}-${index}`}
                  aria-label={`${index + 1}枚目の画像を表示`}
                  aria-pressed={activeIndex === index}
                  className={cn(
                    "h-2.5 w-2.5 rounded-full border border-white/80 transition",
                    activeIndex === index ? "bg-white" : "bg-black/30",
                  )}
                  onClick={() => goTo(index)}
                  type="button"
                >
                  <span className="sr-only">{index + 1}枚目の画像を表示</span>
                </button>
              ))}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
