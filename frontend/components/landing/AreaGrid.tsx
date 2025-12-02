import Link from "next/link";

const WARDS = [
  { slug: "chiyoda", name: "千代田区" },
  { slug: "chuo", name: "中央区" },
  { slug: "minato", name: "港区" },
  { slug: "shinjuku", name: "新宿区" },
  { slug: "bunkyo", name: "文京区" },
  { slug: "taito", name: "台東区" },
  { slug: "sumida", name: "墨田区" },
  { slug: "koto", name: "江東区" },
  { slug: "shinagawa", name: "品川区" },
  { slug: "meguro", name: "目黒区" },
  { slug: "ota", name: "大田区" },
  { slug: "setagaya", name: "世田谷区" },
  { slug: "shibuya", name: "渋谷区" },
  { slug: "nakano", name: "中野区" },
  { slug: "suginami", name: "杉並区" },
  { slug: "toshima", name: "豊島区" },
  { slug: "kita", name: "北区" },
  { slug: "arakawa", name: "荒川区" },
  { slug: "itabashi", name: "板橋区" },
  { slug: "nerima", name: "練馬区" },
  { slug: "adachi", name: "足立区" },
  { slug: "katsushika", name: "葛飾区" },
  { slug: "edogawa", name: "江戸川区" },
];

export function AreaGrid() {
  return (
    <section className="w-full max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
      <div className="mb-10 text-center">
        <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">Browse by Area</h2>
        <p className="mt-2 text-muted-foreground">Find municipal gyms in your ward.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {WARDS.map(ward => (
          <Link
            key={ward.slug}
            href={`/search?city=${ward.slug}`}
            className="group relative flex items-center justify-center rounded-lg border bg-card px-4 py-4 text-center text-sm font-medium shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <span className="absolute inset-0 rounded-lg ring-offset-background transition-all group-hover:ring-2 group-hover:ring-primary/20 group-hover:ring-offset-2" />
            {ward.name}
          </Link>
        ))}
      </div>
    </section>
  );
}
