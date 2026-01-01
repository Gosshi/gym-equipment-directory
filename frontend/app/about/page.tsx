import { Metadata } from "next";
import Link from "next/link";
import { Dumbbell, Map, Search } from "lucide-react";

export const metadata: Metadata = {
  title: "SPOMAPについて | SPOMAP",
  description: "SPOMAP（スポマップ）の運営者情報とサイトの目的について。",
};

export default function AboutPage() {
  return (
    <div className="container mx-auto px-4 py-12 md:px-6">
      <div className="mx-auto max-w-3xl space-y-12">
        {/* Header */}
        <div className="space-y-4 text-center">
          <h1 className="font-heading text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            SPOMAPについて
          </h1>
          <p className="text-lg text-muted-foreground">
            SPOMAP（スポマップ）は、東京都内の公営ジム・スポーツセンターの
            <br className="hidden sm:inline" />
            設備情報を網羅したデータベースサイトです。
          </p>
        </div>

        {/* Mission */}
        <div className="space-y-8">
          <section className="space-y-4">
            <h2 className="text-xl font-bold text-foreground">サイトの目的</h2>
            <p className="leading-relaxed text-muted-foreground">
              「近所の公営ジムにパワーラックはあるかな？」「ダンベルは何キロまであるんだろう？」
              <br />
              そんな疑問を持ったことはありませんか？
            </p>
            <p className="leading-relaxed text-muted-foreground">
              一般的な地図アプリや公式サイトでは、マシンの詳細なラインナップまでは分からないことがほとんどです。
              SPOMAPは、実際にトレーニングを行うユーザーの視点で、各施設の設備情報を詳細に収集・公開することで、
              「自分に合ったジム探し」をサポートします。
            </p>
          </section>

          {/* Features */}
          <section className="grid gap-6 sm:grid-cols-3">
            <div className="rounded-lg border border-border bg-card p-6 text-center">
              <div className="mb-4 flex justify-center">
                <Search className="h-8 w-8 text-accent" />
              </div>
              <h3 className="mb-2 font-bold">詳細な設備検索</h3>
              <p className="text-xs text-muted-foreground">
                パワーラックの有無、ダンベルの重さなど、細かい条件で検索可能。
              </p>
            </div>
            <div className="rounded-lg border border-border bg-card p-6 text-center">
              <div className="mb-4 flex justify-center">
                <Map className="h-8 w-8 text-accent" />
              </div>
              <h3 className="mb-2 font-bold">地図から探す</h3>
              <p className="text-xs text-muted-foreground">
                自宅や職場の近くにある公営ジムを地図上で直感的に探せます。
              </p>
            </div>
            <div className="rounded-lg border border-border bg-card p-6 text-center">
              <div className="mb-4 flex justify-center">
                <Dumbbell className="h-8 w-8 text-accent" />
              </div>
              <h3 className="mb-2 font-bold">最新の情報を維持</h3>
              <p className="text-xs text-muted-foreground">
                定期的な情報の更新を行い、常に最新の設備情報を提供します。
              </p>
            </div>
          </section>

          {/* Operation Info */}
          <section className="space-y-4 rounded-xl border border-border bg-muted/40 p-6">
            <h2 className="text-lg font-bold text-foreground">運営者情報</h2>
            <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-3">
              <div className="space-y-1">
                <dt className="font-medium text-muted-foreground">サイト名</dt>
                <dd className="font-semibold">SPOMAP（スポマップ）</dd>
              </div>
              <div className="space-y-1">
                <dt className="font-medium text-muted-foreground">運営</dt>
                <dd className="font-semibold">SPOMAP運営事務局</dd>
              </div>
              <div className="space-y-1">
                <dt className="font-medium text-muted-foreground">連絡先</dt>
                <dd className="font-semibold">spomapjp[at]gmail.com</dd>
              </div>
            </dl>
          </section>

          {/* CTA */}
          <section className="text-center">
            <p className="mb-6 text-muted-foreground">
              不正確な情報にお気づきの際は、
              <Link href="/contact" className="text-primary hover:underline">
                お問い合わせ
              </Link>
              よりご連絡いただけますと幸いです。
            </p>
            <Link
              href="/gyms"
              className="inline-flex h-10 items-center justify-center rounded-md bg-accent px-8 text-sm font-medium text-accent-foreground shadow transition-colors hover:bg-accent/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              ジムを探しにいく
            </Link>
          </section>
        </div>
      </div>
    </div>
  );
}
