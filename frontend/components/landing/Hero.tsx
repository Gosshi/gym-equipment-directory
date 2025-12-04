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

      <div className="relative z-10 flex max-w-4xl flex-col items-center gap-8 px-4">
        {/* Main Heading */}
        <div className="flex flex-col items-center gap-2">
          <span className="font-mono text-sm font-bold tracking-[0.2em] text-accent uppercase">
            Tokyo Public Gym Directory
          </span>
          <h1 className="font-heading text-7xl font-black uppercase tracking-tighter text-foreground sm:text-8xl md:text-9xl">
            IRON <span className="text-stroke text-transparent">MAP</span>
          </h1>
          <p className="max-w-xl text-lg text-muted-foreground font-body">
            Find your forge. Discover affordable municipal gyms equipped for serious training.
          </p>
        </div>

        {/* Search Bar */}
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
              placeholder="SEARCH EQUIPMENT (E.G. POWER RACK)..."
              className="h-14 rounded-none border-2 border-r-0 border-border bg-card/80 pl-12 font-mono text-lg uppercase tracking-wide backdrop-blur focus-visible:border-accent focus-visible:ring-0"
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
            />
          </div>
          <Button
            type="submit"
            className="h-14 rounded-none border-2 border-accent bg-accent px-8 font-heading text-xl font-bold uppercase tracking-widest text-accent-foreground hover:bg-accent/90"
          >
            Search
          </Button>
        </form>

        {/* Popular Tags */}
        <div className="flex flex-wrap justify-center gap-3">
          {[
            { label: "Power Rack", query: "Power Rack", icon: Dumbbell },
            { label: "Smith Machine", query: "Smith Machine", icon: Dumbbell },
            { label: "Minato-ku", query: "Minato", icon: MapPin },
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
    </section>
  );
}
