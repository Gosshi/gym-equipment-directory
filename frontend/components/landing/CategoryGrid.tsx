import Link from "next/link";

const CATEGORIES = [
  {
    slug: "gym",
    path: "/gym",
    name: "ジム",
    en: "GYM",
    description: "トレーニングジム・フィットネス",
    colorClass: "group-hover:border-emerald-500 group-hover:text-emerald-500",
    accentClass: "group-hover:border-emerald-500",
  },
  {
    slug: "pool",
    path: "/pool",
    name: "プール",
    en: "POOL",
    description: "水泳・温水プール",
    colorClass: "group-hover:border-cyan-500 group-hover:text-cyan-500",
    accentClass: "group-hover:border-cyan-500",
  },
  {
    slug: "court",
    path: "/tennis",
    name: "テニスコート",
    en: "TENNIS",
    description: "テニス・スポーツコート",
    colorClass: "group-hover:border-amber-500 group-hover:text-amber-500",
    accentClass: "group-hover:border-amber-500",
  },
  {
    slug: "hall",
    path: "/hall",
    name: "体育館",
    en: "GYMNASIUM",
    description: "バスケ・バレー・バドミントン",
    colorClass: "group-hover:border-violet-500 group-hover:text-violet-500",
    accentClass: "group-hover:border-violet-500",
  },
  {
    slug: "field",
    path: "/field",
    name: "グラウンド",
    en: "FIELD",
    description: "野球場・サッカー場",
    colorClass: "group-hover:border-orange-500 group-hover:text-orange-500",
    accentClass: "group-hover:border-orange-500",
  },
  {
    slug: "martial_arts",
    path: "/martial-arts",
    name: "武道場",
    en: "MARTIAL ARTS",
    description: "柔道・剣道・空手",
    colorClass: "group-hover:border-red-500 group-hover:text-red-500",
    accentClass: "group-hover:border-red-500",
  },
  {
    slug: "archery",
    path: "/archery",
    name: "弓道場",
    en: "ARCHERY",
    description: "弓道・アーチェリー",
    colorClass: "group-hover:border-teal-500 group-hover:text-teal-500",
    accentClass: "group-hover:border-teal-500",
  },
];

export function CategoryGrid() {
  return (
    <section className="w-full max-w-7xl px-4 py-24 sm:px-6 lg:px-8">
      <div className="mb-12 flex flex-col items-center text-center">
        <span className="font-mono text-sm font-bold tracking-[0.2em] text-accent uppercase">
          カテゴリ選択
        </span>
        <h2 className="font-heading text-4xl font-bold uppercase tracking-tighter sm:text-5xl">
          施設タイプから探す
        </h2>
        <div className="mt-4 h-1 w-24 bg-accent" />
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7">
        {CATEGORIES.map(category => (
          <Link
            key={category.slug}
            href={category.path}
            className={`group relative flex flex-col items-center justify-center gap-2 overflow-hidden border border-border bg-card/30 p-6 text-center backdrop-blur-sm transition-all hover:bg-accent/5 ${category.colorClass}`}
          >
            {/* Corner Accents */}
            <div
              className={`absolute left-0 top-0 h-2 w-2 border-l-2 border-t-2 border-transparent transition-colors ${category.accentClass}`}
            />
            <div
              className={`absolute right-0 top-0 h-2 w-2 border-r-2 border-t-2 border-transparent transition-colors ${category.accentClass}`}
            />
            <div
              className={`absolute bottom-0 left-0 h-2 w-2 border-b-2 border-l-2 border-transparent transition-colors ${category.accentClass}`}
            />
            <div
              className={`absolute bottom-0 right-0 h-2 w-2 border-b-2 border-r-2 border-transparent transition-colors ${category.accentClass}`}
            />

            <span className="font-heading text-xl font-bold tracking-wide text-foreground transition-colors sm:text-2xl">
              {category.name}
            </span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground transition-colors">
              {category.en}
            </span>
            <span className="mt-1 text-xs text-muted-foreground/80 transition-colors">
              {category.description}
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
