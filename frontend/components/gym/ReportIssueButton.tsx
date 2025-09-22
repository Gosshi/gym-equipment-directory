import Link from "next/link";
import { Flag } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface ReportIssueButtonProps {
  slug: string;
  gymName: string;
}

export function ReportIssueButton({ slug, gymName }: ReportIssueButtonProps) {
  const reportUrl = `/gyms/${encodeURIComponent(slug)}/report`;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button type="button" variant="outline">
          <Flag aria-hidden className="mr-2 h-4 w-4" />
          問題を報告
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>問題を報告</DialogTitle>
          <DialogDescription>
            {gymName} の情報に誤りや更新が必要な点がある場合は、以下のフォームからご連絡ください。
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 text-sm text-muted-foreground">
          <p>フォームでは住所・設備・営業時間などの最新情報をお知らせいただけます。</p>
          <p>正式な投稿機能は後続ステップで追加予定です。それまではリンク先で詳細をご入力ください。</p>
        </div>
        <DialogFooter>
          <Button asChild>
            <Link href={reportUrl}>報告フォームへ移動</Link>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
