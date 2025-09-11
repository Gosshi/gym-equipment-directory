import type { Metadata } from "next";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "Gym Directory",
  description: "Search gyms by equipment and location",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>
        {/* Minimal baseline styles */}
        <style>{`
          :root { color-scheme: light; }
          * { box-sizing: border-box; }
          body { margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji"; }
          a { color: #0b5bd3; text-decoration: none; }
          a:hover { text-decoration: underline; }
          header { border-bottom: 1px solid #e5e7eb; padding: 12px 16px; }
          main { max-width: 960px; margin: 0 auto; padding: 16px; }
          h1, h2, h3 { margin: 0 0 8px; }
          .stack { display: grid; gap: 12px; }
          .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
          .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; }
          .muted { color: #6b7280; }
          .btn { display:inline-flex; align-items:center; gap:6px; background:#111827; color:#fff; border-radius:6px; padding:8px 12px; border:0; cursor:pointer; }
          .btn.secondary { background:#374151; }
          .btn:disabled { opacity: .6; cursor: not-allowed; }
          label { font-size: 0.9rem; }
          input[type="text"], select { padding: 6px 8px; border:1px solid #d1d5db; border-radius:6px; }
          fieldset { border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px 12px; }
          legend { padding: 0 6px; font-size: .9rem; }
        `}</style>
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

