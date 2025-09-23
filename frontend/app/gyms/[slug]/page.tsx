import Link from "next/link";

import { GymDetailPage } from "./GymDetailPage";

export default function GymDetailRoute({ params }: { params: { slug: string } }) {
  const { slug } = params;

  return (
    <>
      <GymDetailPage slug={slug} />
      <div className="px-4 pb-10">
        <div className="mx-auto w-full max-w-5xl">
          <Link
            aria-label="このジムの情報を報告する"
            className="mt-6 inline-flex text-sm font-medium text-muted-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            href={`/gyms/${slug}/report`}
          >
            このジム情報に問題がありますか？報告する
          </Link>
        </div>
      </div>
    </>
  );
}
