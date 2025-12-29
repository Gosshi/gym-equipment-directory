import type { Metadata } from "next";
import { Manrope, Oswald } from "next/font/google";

import { AuthProvider } from "@/auth/AuthProvider";
import { AppFooter } from "@/components/common/Footer";
import { AppHeader } from "@/components/common/Header";
import { Toaster } from "@/components/ui/toaster";
import { QueryProvider } from "@/providers/QueryProvider";

import "./globals.css";
import { AdSense } from "@/components/ads/AdSense";

const oswald = Oswald({
  subsets: ["latin"],
  variable: "--font-oswald",
  display: "swap",
});

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SPOMAP | 公式サイトなしでもOK。東京都内の公営ジム検索",
  description:
    "SPOMAP（スポマップ）は東京都内の公営ジム・スポーツセンターの設備情報を網羅したデータベースです。パワーラック、ダンベル、プールなどの設備からジムを検索できます。",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja" className={`${oswald.variable} ${manrope.variable}`}>
      <body className="bg-background font-sans text-foreground antialiased selection:bg-primary selection:text-primary-foreground">
        <AuthProvider>
          <QueryProvider>
            <div className="flex min-h-screen flex-col">
              <AppHeader />
              <div className="flex-1">{children}</div>
              <AppFooter />
              <Toaster />
            </div>
            {process.env.NEXT_PUBLIC_GOOGLE_ADSENSE_ID && (
              <AdSense pId={process.env.NEXT_PUBLIC_GOOGLE_ADSENSE_ID} />
            )}
          </QueryProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
