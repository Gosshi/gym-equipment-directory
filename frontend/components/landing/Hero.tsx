"use client";

import { Search } from "lucide-react";
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
    <section className="relative flex w-full flex-col items-center justify-center overflow-hidden bg-gradient-to-b from-muted/50 to-background px-4 py-24 text-center sm:py-32 md:px-8">
      <div className="relative z-10 flex max-w-3xl flex-col items-center gap-6">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl md:text-6xl">
          <span className="block text-foreground">Find the Perfect</span>
          <span className="block bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
            Public Gym in Tokyo
          </span>
        </h1>
        <p className="max-w-2xl text-lg text-muted-foreground sm:text-xl">
          Discover affordable municipal gyms with the equipment you need.
          <br className="hidden sm:inline" /> Search by area, machine type, and more.
        </p>

        <form onSubmit={handleSearch} className="flex w-full max-w-md items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search by keyword (e.g. bench press)..."
              className="pl-9"
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
            />
          </div>
          <Button type="submit">Search</Button>
        </form>

        <div className="flex flex-wrap justify-center gap-2 text-sm text-muted-foreground">
          <span>Popular:</span>
          <button
            type="button"
            onClick={() => router.push("/search?q=Power+Rack")}
            className="hover:text-primary hover:underline"
          >
            Power Rack
          </button>
          <span>•</span>
          <button
            type="button"
            onClick={() => router.push("/search?q=Smith+Machine")}
            className="hover:text-primary hover:underline"
          >
            Smith Machine
          </button>
          <span>•</span>
          <button
            type="button"
            onClick={() => router.push("/search?q=Dumbbell")}
            className="hover:text-primary hover:underline"
          >
            Dumbbell
          </button>
        </div>
      </div>
    </section>
  );
}
