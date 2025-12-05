import Link from "next/link";

const WARDS = [
  { slug: "chiyoda", name: "千代田区", en: "CHIYODA" },
  { slug: "chuo", name: "中央区", en: "CHUO" },
  { slug: "minato", name: "港区", en: "MINATO" },
  { slug: "shinjuku", name: "新宿区", en: "SHINJUKU" },
  { slug: "bunkyo", name: "文京区", en: "BUNKYO" },
  { slug: "taito", name: "台東区", en: "TAITO" },
  { slug: "sumida", name: "墨田区", en: "SUMIDA" },
  { slug: "koto", name: "江東区", en: "KOTO" },
  { slug: "shinagawa", name: "品川区", en: "SHINAGAWA" },
  { slug: "meguro", name: "目黒区", en: "MEGURO" },
  { slug: "ota", name: "大田区", en: "OTA" },
  { slug: "setagaya", name: "世田谷区", en: "SETAGAYA" },
  { slug: "shibuya", name: "渋谷区", en: "SHIBUYA" },
  { slug: "nakano", name: "中野区", en: "NAKANO" },
  { slug: "suginami", name: "杉並区", en: "SUGINAMI" },
  { slug: "toshima", name: "豊島区", en: "TOSHIMA" },
  { slug: "kita", name: "北区", en: "KITA" },
  { slug: "arakawa", name: "荒川区", en: "ARAKAWA" },
  { slug: "itabashi", name: "板橋区", en: "ITABASHI" },
  { slug: "nerima", name: "練馬区", en: "NERIMA" },
  { slug: "adachi", name: "足立区", en: "ADACHI" },
  { slug: "katsushika", name: "葛飾区", en: "KATSUSHIKA" },
  { slug: "edogawa", name: "江戸川区", en: "EDOGAWA" },
];

export function AreaGrid() {
  return (
    <section className="w-full max-w-7xl px-4 py-24 sm:px-6 lg:px-8">
      <div className="mb-12 flex flex-col items-center text-center">
        <span className="font-mono text-sm font-bold tracking-[0.2em] text-accent uppercase">
          エリア選択
        </span>
        <h2 className="font-heading text-4xl font-bold uppercase tracking-tighter sm:text-5xl">
          エリアから探す
        </h2>
        <div className="mt-4 h-1 w-24 bg-accent" />
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
        {WARDS.map(ward => (
          <Link
            key={ward.slug}
            href={`/search?city=${ward.slug}`}
            className="group relative flex flex-col items-center justify-center gap-1 overflow-hidden border border-border bg-card/30 p-6 text-center backdrop-blur-sm transition-all hover:border-accent hover:bg-accent/5"
          >
            {/* Corner Accents */}
            <div className="absolute left-0 top-0 h-2 w-2 border-l-2 border-t-2 border-transparent transition-colors group-hover:border-accent" />
            <div className="absolute right-0 top-0 h-2 w-2 border-r-2 border-t-2 border-transparent transition-colors group-hover:border-accent" />
            <div className="absolute bottom-0 left-0 h-2 w-2 border-b-2 border-l-2 border-transparent transition-colors group-hover:border-accent" />
            <div className="absolute bottom-0 right-0 h-2 w-2 border-b-2 border-r-2 border-transparent transition-colors group-hover:border-accent" />

            <span className="font-heading text-2xl font-bold tracking-wide text-foreground group-hover:text-accent">
              {ward.name}
            </span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground group-hover:text-accent/70">
              {ward.en}
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
