import { AreaGrid } from "@/components/landing/AreaGrid";
import { Hero } from "@/components/landing/Hero";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center">
      <Hero />
      <AreaGrid />
    </main>
  );
}
