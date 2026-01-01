import { Metadata } from "next";
import { Mail } from "lucide-react";

export const metadata: Metadata = {
  title: "お問い合わせ | SPOMAP",
  description: "SPOMAPへのお問い合わせはこちらから。",
};

export default function ContactPage() {
  return (
    <div className="container mx-auto px-4 py-12 md:px-6">
      <div className="mx-auto max-w-2xl space-y-8 text-center">
        <div>
          <h1 className="mb-4 font-heading text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            お問い合わせ
          </h1>
          <p className="text-lg text-muted-foreground">
            ご質問、ご要望、バグ報告などがございましたら、
            <br className="hidden sm:inline" />
            以下のメールアドレスまでお気軽にご連絡ください。
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
          <div className="mb-6 flex justify-center">
            <div className="rounded-full bg-accent/10 p-4">
              <Mail className="h-8 w-8 text-accent" />
            </div>
          </div>
          <h2 className="mb-2 text-xl font-bold text-foreground">メールでのお問い合わせ</h2>
          <p className="mb-6 text-sm text-muted-foreground">通常24時間以内に返信いたします。</p>
          <a
            href="mailto:info@spomapjp.com"
            className="inline-flex items-center justify-center rounded-md bg-primary px-8 py-3 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
            info@spomapjp.com
          </a>
        </div>

        <p className="text-sm text-muted-foreground">
          ※ 頂いたお問い合わせ内容によっては、返信にお時間をいただく場合や
          <br />
          お答えできない場合がございます。あらかじめご了承ください。
        </p>
      </div>
    </div>
  );
}
