"use client";

import Script from "next/script";

type Props = {
  pId: string;
};

export function AdSense({ pId }: Props) {
  if (!pId) return null;

  return (
    <Script
      async
      src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${pId}`}
      crossOrigin="anonymous"
      strategy="afterInteractive"
    />
  );
}
