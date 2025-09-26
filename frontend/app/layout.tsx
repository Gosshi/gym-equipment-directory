import type { Metadata } from "next";

import { AuthProvider } from "@/auth/AuthProvider";
import { AppHeader } from "@/components/common/Header";
import { Toaster } from "@/components/ui/toaster";
import { ReactQueryProvider } from "@/providers/ReactQueryProvider";

import "./globals.css";

export const metadata: Metadata = {
  title: "Gym Equipment Directory",
  description: "Check the health of the Gym Equipment Directory API.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body className="bg-background font-sans text-foreground antialiased">
        <ReactQueryProvider>
          <AuthProvider>
            <div className="flex min-h-screen flex-col">
              <AppHeader />
              <div className="flex-1">{children}</div>
              <Toaster />
            </div>
          </AuthProvider>
        </ReactQueryProvider>
      </body>
    </html>
  );
}
