import type { Metadata } from "next";
import Providers from "./providers";
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
            <a href="/search"><strong>Gym Directory</strong></a>
          </div>
        </header>
        <Providers>
          <main>{children}</main>
        </Providers>
      </body>
    </html>
  );
}
