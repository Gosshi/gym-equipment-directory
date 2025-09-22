import { HealthCheckCard } from "@/components/health-check-card";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center px-4 py-16">
      <section className="flex w-full max-w-3xl flex-1 flex-col gap-8">
        <header className="space-y-3 text-center sm:text-left">
          <p className="text-sm uppercase tracking-wide text-muted-foreground">Gym Equipment Directory</p>
          <h1 className="text-3xl font-bold sm:text-4xl">API ヘルスチェック</h1>
          <p className="text-base text-muted-foreground">
            下記のカードで /health エンドポイントの結果を確認できます。環境変数
            <span className="font-mono"> NEXT_PUBLIC_API_BASE_URL </span>
            を切り替えて API を指定してください。
          </p>
        </header>
        <div className="flex justify-center sm:justify-start">
          <HealthCheckCard />
        </div>
      </section>
    </main>
  );
}
