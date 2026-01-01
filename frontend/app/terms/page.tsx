import { Metadata } from "next";

export const metadata: Metadata = {
  title: "利用規約 | SPOMAP",
  description: "SPOMAPの利用規約です。",
};

export default function TermsPage() {
  return (
    <div className="container mx-auto px-4 py-12 md:px-6">
      <div className="mx-auto max-w-3xl space-y-8">
        <div>
          <h1 className="mb-2 font-heading text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            利用規約
          </h1>
          <p className="text-muted-foreground">制定日: 2024年1月1日</p>
        </div>

        <div className="prose prose-gray max-w-none dark:prose-invert">
          <p>
            SPOMAP（以下、「当サイト」）を利用される際は、以下の規約に同意したものとみなします。
          </p>

          <h3>1. 免責事項</h3>
          <p>
            当サイトに掲載されている情報の正確性には万全を期していますが、利用者が当サイトの情報を用いて行う一切の行為に関して、運営者は何ら責任を負うものではありません。
            当サイトの利用によって生じた損害等について、運営者は一切の責任を負いかねます。
          </p>

          <h3>2. 禁止事項</h3>
          <p>当サイトの利用に際し、以下の行為を禁止します。</p>
          <ul>
            <li>法令または公序良俗に違反する行為</li>
            <li>運営者または第三者の権利を侵害する行為</li>
            <li>当サイトの運営を妨害する行為</li>
            <li>その他、運営者が不適切と判断する行為</li>
          </ul>

          <h3>3. 規約の変更</h3>
          <p>
            運営者は、事前の通知なく本規約を変更できるものとします。変更後の規約は、当サイトに掲載された時点で効力を生じるものとします。
          </p>

          <h3>4. 準拠法・管轄</h3>
          <p>
            本規約の解釈は日本法を準拠法とします。当サイトに関して紛争が生じた場合は、東京地方裁判所を第一審の専属的合意管轄裁判所とします。
          </p>

          <h3>5. お問い合わせ</h3>
          <p>
            本規約に関するお問い合わせは、<a href="mailto:spomapjp@gmail.com">spomapjp@gmail.com</a>
            までお願いいたします。
          </p>
        </div>
      </div>
    </div>
  );
}
