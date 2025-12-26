"use client";

import { Search, MapPin, Dumbbell } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function Hero() {
  const router = useRouter();
  const [keyword, setKeyword] = useState("");

  const handleSearch = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!keyword.trim()) {
        router.push("/search");
        return;
      }
      const params = new URLSearchParams();
      params.set("q", keyword.trim());
      router.push(`/search?${params.toString()}`);
    },
    [keyword, router],
  );

  return (
    <section className="relative flex w-full flex-col items-center justify-center overflow-hidden bg-background py-32 text-center md:py-48">
      {/* Background Grid & Noise */}
      <div className="absolute inset-0 z-0 bg-grid-pattern opacity-20" />
      <div className="absolute inset-0 z-0 bg-[url('/noise.png')] opacity-5 mix-blend-overlay" />

      {/* Decorative Elements */}
      <div className="absolute left-4 top-4 font-mono text-xs text-muted-foreground/50">
        SYS.STATUS: ONLINE
        <br />
        LOC: TOKYO, JP
      </div>
      <div className="absolute right-4 bottom-4 font-mono text-xs text-muted-foreground/50 text-right">
        EST. 2024
        <br />
        IRON MAP PROJECT
      </div>

      <div className="relative z-10 flex h-full flex-col items-center justify-center px-4 text-center">
        <div className="mb-6 inline-flex items-center gap-2 border border-accent/30 bg-accent/10 px-3 py-1 backdrop-blur-sm">
          <span className="h-2 w-2 animate-pulse bg-accent" />
          <span className="font-mono text-xs font-bold tracking-widest text-accent">
            SYSTEM: ONLINE
          </span>
        </div>

        <h1 className="mb-4 font-heading text-6xl font-black uppercase tracking-tighter text-foreground sm:text-7xl md:text-9xl">
          <span className="block text-stroke-sm md:text-stroke text-transparent">IRON</span>
          <span className="block text-accent">MAP</span>
        </h1>

        <p className="mb-12 max-w-2xl font-mono text-sm text-muted-foreground sm:text-base md:text-lg">
          東京都内の公営ジムを網羅したデータベース。
          <br className="hidden sm:block" />
          あなたの鍛錬の場を見つけよう。
        </p>

        <div className="w-full max-w-xl">
          <form
            onSubmit={handleSearch}
            className="flex w-full max-w-lg items-stretch gap-0 shadow-2xl"
          >
            <div className="relative flex-1 group">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-accent transition-colors">
                <Search className="h-5 w-5" />
              </div>
              <Input
                type="search"
                placeholder="設備名で検索 (例: パワーラック)..."
                className="h-14 border-2 border-accent/50 bg-background/50 text-lg backdrop-blur-md transition-all focus-within:border-accent focus-within:bg-background/80 focus-within:ring-4 focus-within:ring-accent/20 pl-12 font-mono uppercase tracking-wide focus-visible:ring-0"
                value={keyword}
                onChange={e => setKeyword(e.target.value)}
              />
            </div>
            <Button
              type="submit"
              className="group relative h-14 overflow-hidden rounded-none border-2 border-foreground bg-foreground px-8 font-heading text-xl font-bold uppercase tracking-widest text-background shadow-[0_0_30px_rgba(255,255,255,0.3)] transition-all duration-300 hover:scale-105 hover:shadow-[0_0_50px_rgba(255,255,255,0.5)]"
            >
              <span className="relative z-10 flex items-center gap-2">
                <Search className="h-5 w-5" />
                検索
              </span>
              {/* Shine effect on hover */}
              <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-500 group-hover:translate-x-full" />
            </Button>
          </form>

          {/* Popular Tags */}
          <div className="flex flex-wrap justify-center gap-3">
            {[
              { label: "パワーラック", query: "パワーラック", icon: Dumbbell },
              { label: "スミスマシン", query: "スミスマシン", icon: Dumbbell },
              { label: "港区", query: "港区", icon: MapPin },
            ].map(tag => (
              <button
                key={tag.label}
                type="button"
                onClick={() => router.push(`/search?q=${tag.query}`)}
                className="group flex items-center gap-2 border border-border bg-card/50 px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-muted-foreground transition-all hover:border-accent hover:bg-accent/10 hover:text-accent"
              >
                <tag.icon className="h-3 w-3" />
                {tag.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
