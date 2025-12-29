"use client";

import { useEffect } from "react";

type Props = {
  slotId?: string; // Optional for auto-ads, required for specific units
  format?: "auto" | "fluid" | "rectangle";
  responsive?: boolean;
  className?: string;
};

export function AdBanner({ slotId, format = "auto", responsive = true, className = "" }: Props) {
  useEffect(() => {
    try {
      // @ts-ignore
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch (err) {
      console.error("AdSense error:", err);
    }
  }, []);

  const pId = process.env.NEXT_PUBLIC_GOOGLE_ADSENSE_ID;

  if (!pId) {
    if (process.env.NODE_ENV === "development") {
      return (
        <div
          className={`bg-gray-100 dark:bg-zinc-800 border border-dashed border-gray-300 dark:border-zinc-700 flex items-center justify-center text-xs text-muted-foreground p-4 ${className}`}
        >
          [AdSense Placeholder]
        </div>
      );
    }
    return null;
  }

  return (
    <div className={`overflow-hidden ${className}`}>
      <ins
        className="adsbygoogle"
        style={{ display: "block" }}
        data-ad-client={pId}
        data-ad-slot={slotId}
        data-ad-format={format}
        data-full-width-responsive={responsive}
      />
    </div>
  );
}
