import type { Metadata } from "next";
import Providers from "./providers";
import { ToastProvider } from "@/components/Toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gym Directory",
  description: "Search gyms by equipment and location",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <header>
          <div style={{ maxWidth: 960, margin: "0 auto" }} className="row">
            <a href="/search">
              <strong>Gym Directory</strong>
            </a>
          </div>
        </header>
        <Providers>
          <ToastProvider>
            <main>{children}</main>
          </ToastProvider>
        </Providers>
      </body>
    </html>
  );
}
