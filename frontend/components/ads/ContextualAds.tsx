import { ExternalLink, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { resolveContextualAdGroups, type ContextualGym } from "@/lib/affiliateProducts";

const LINK_CLASS_NAME =
  "inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium " +
  "text-primary-foreground transition-colors hover:bg-primary/90";

export function ContextualAds({ gym }: { gym: ContextualGym }) {
  const groups = resolveContextualAdGroups(gym);
  if (groups.length === 0) {
    return null;
  }

  const hasAffiliate = groups.some(group => group.links.some(link => link.isAffiliate));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5" />
          施設タイプ別のおすすめ
          <Badge variant="outline" className="text-[10px]">
            PR
          </Badge>
        </CardTitle>
        <CardDescription>利用目的に合わせた関連リンクをまとめています。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {groups.map(group => (
          <div key={group.key} className="rounded-lg border border-border/60 bg-card/50 p-4">
            <div className="text-sm font-semibold text-foreground">{group.title}</div>
            <p className="mt-1 text-xs text-muted-foreground">{group.description}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {group.links.map(link => (
                <a
                  key={link.id}
                  href={link.href}
                  target="_blank"
                  rel="sponsored noopener noreferrer"
                  className={LINK_CLASS_NAME}
                >
                  <ExternalLink className="h-3 w-3" />
                  {link.label}
                </a>
              ))}
            </div>
          </div>
        ))}
        {hasAffiliate ? (
          <p className="text-xs text-muted-foreground">
            ※ 上記リンクはアフィリエイトリンクを含みます
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
