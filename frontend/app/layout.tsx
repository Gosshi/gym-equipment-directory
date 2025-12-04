import type { Metadata } from "next";
import { Manrope, Oswald } from "next/font/google";

import { AuthProvider } from "@/auth/AuthProvider";
import { AppHeader } from "@/components/common/Header";
import { Toaster } from "@/components/ui/toaster";
import { QueryProvider } from "@/providers/QueryProvider";

import "./globals.css";

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
  title: "IRON MAP | Gym Equipment Directory",
  description: "Find the perfect gym for your workout. Filter by equipment, location, and vibe.",
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
              <Toaster />
            </div>
          </QueryProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
