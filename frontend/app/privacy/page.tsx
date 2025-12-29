import { Container } from "@/components/common/Container";
import { type Metadata } from "next";

export const metadata: Metadata = {
  title: "プライバシーポリシー | 公営ジム検索くん",
  description:
    "公営ジム検索くんのプライバシーポリシーです。個人情報の取り扱い、Cookie、広告配信について説明します。",
};

export default function PrivacyPage() {
  return (
    <Container className="py-12">
      <div className="prose prose-zinc dark:prose-invert max-w-3xl mx-auto">
        <h1>プライバシーポリシー</h1>
        <p className="text-muted-foreground text-sm">最終更新日: 2025年12月29日</p>

        <section className="mt-8">
          <h2>1. 個人情報の利用目的</h2>
          <p>
            当サイトでは、お問い合わせや記事へのコメントの際、名前やメールアドレス等の個人情報を入力いただく場合がございます。
            取得した個人情報は、お問い合わせに対する回答や必要な情報を電子メールなどをでご連絡する場合に利用させていただくものであり、これらの目的以外では利用いたしません。
          </p>
        </section>

        <section className="mt-8">
          <h2>2. 広告について</h2>
          <p>
            当サイトでは、第三者配信の広告サービス（Google
            AdSense）を利用しており、ユーザーの興味に応じた商品やサービスの広告を表示するため、クッキー（Cookie）を使用しております。
            クッキーを使用することで当サイトはお客様のコンピュータを識別できるようになりますが、お客様個人を特定できるものではありません。
          </p>
          <p>
            Cookieを無効にする方法やGoogle AdSenseに関する詳細は
            <a
              href="https://policies.google.com/technologies/ads?hl=ja"
              target="_blank"
              rel="noopener noreferrer"
            >
              「広告 – ポリシーと規約 – Google」
            </a>
            をご確認ください。
          </p>
        </section>

        <section className="mt-8">
          <h2>3. アクセス解析ツールについて</h2>
          <p>
            当サイトでは、Googleによるアクセス解析ツール「Googleアナリティクス」を利用しています。
            このGoogleアナリティクスはトラフィックデータの収集のためにクッキー（Cookie）を使用しております。
            トラフィックデータは匿名で収集されており、個人を特定するものではありません。
          </p>
        </section>

        <section className="mt-8">
          <h2>4. 免責事項</h2>
          <p>
            当サイトからのリンクやバナーなどで移動したサイトで提供される情報、サービス等について一切の責任を負いません。
            また当サイトのコンテンツ・情報について、できる限り正確な情報を提供するように努めておりますが、正確性や安全性を保証するものではありません。
            情報が古くなっていることもございます。
            当サイトに掲載された内容によって生じた損害等の一切の責任を負いかねますのでご了承ください。
          </p>
        </section>
      </div>
    </Container>
  );
}
