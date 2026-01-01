"use client";

import Link from "next/link";
import { Github, Twitter, Mail } from "lucide-react";

export function AppFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-background">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        {/* Main Grid */}
        <div className="grid gap-8 lg:grid-cols-4">
          {/* Brand Section */}
          <div className="space-y-4 lg:col-span-2">
            <div className="flex items-center gap-2">
              <span className="font-heading text-2xl font-black uppercase tracking-tighter text-foreground">
                SPO<span className="text-accent">MAP</span>
              </span>
            </div>
            <p className="max-w-md font-mono text-xs leading-relaxed text-muted-foreground">
              公営スポーツ施設の設備情報を検索。
              <br />
              施設カテゴリや設備で絞り込みできます。
            </p>
            <div className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest text-muted-foreground/50">
              <span className="inline-block h-1.5 w-1.5 animate-pulse bg-accent" />
              <span>SYS.STATUS: OPERATIONAL</span>
            </div>
          </div>

          {/* Links Section */}
          <div className="space-y-4">
            <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
              NAVIGATION
            </h3>
            <ul className="space-y-2">
              <li>
                <Link
                  href="/gyms"
                  className="font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
                >
                  施設検索
                </Link>
              </li>
              <li>
                <Link
                  href="/gyms/nearby"
                  className="font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
                >
                  現在地から探す
                </Link>
              </li>
              <li>
                <Link
                  href="/map"
                  className="font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
                >
                  地図で探す
                </Link>
              </li>
              <li>
                <Link
                  href="/me/favorites"
                  className="font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
                >
                  お気に入り
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal Section */}
          <div className="space-y-4">
            <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-accent">
              LEGAL
            </h3>
            <ul className="space-y-2">
              <li>
                <Link
                  href="/about"
                  className="font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
                >
                  運営者情報
                </Link>
              </li>
              <li>
                <Link
                  href="/terms"
                  className="font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
                >
                  利用規約
                </Link>
              </li>
              <li>
                <Link
                  href="/privacy"
                  className="font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
                >
                  プライバシーポリシー
                </Link>
              </li>
              <li>
                <Link
                  href="/contact"
                  className="font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
                >
                  お問い合わせ
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Divider */}
        <div className="my-8 h-px bg-gradient-to-r from-transparent via-border to-transparent" />

        {/* Bottom Section */}
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground/60">
            &copy; {currentYear} SPOMAP. ALL RIGHTS RESERVED.
          </p>
          <div className="flex items-center gap-4">
            {/* 
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground/60 transition-colors hover:text-foreground"
              aria-label="GitHub"
            >
              <Github className="h-4 w-4" />
            </a>
            <a
              href="https://twitter.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground/60 transition-colors hover:text-foreground"
              aria-label="Twitter"
            >
              <Twitter className="h-4 w-4" />
            </a>
             */}
            <Link
              href="/contact"
              className="text-muted-foreground/60 transition-colors hover:text-foreground"
              aria-label="Contact"
            >
              <Mail className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
