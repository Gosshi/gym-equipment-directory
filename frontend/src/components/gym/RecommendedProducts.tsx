"use client";

import { ExternalLink, ShoppingBag } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type CategoryProducts,
  buildAmazonSearchUrl,
  buildRakutenSearchUrl,
  getProductsForCategories,
  isAffiliateEnabled,
} from "@/lib/affiliateProducts";

interface RecommendedProductsProps {
  categories: string[];
}

export function RecommendedProducts({ categories }: RecommendedProductsProps) {
  // アフィリエイトが無効な場合は表示しない
  if (!isAffiliateEnabled()) {
    return null;
  }

  const categoryProducts = getProductsForCategories(categories);
  if (!categoryProducts) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShoppingBag className="h-5 w-5" />
          おすすめグッズ
        </CardTitle>
        <CardDescription>
          {categoryProducts.categoryLabel}を利用するならこちらがおすすめ
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-2">
          {categoryProducts.products.map(product => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
        <p className="mt-4 text-xs text-muted-foreground">
          ※ 上記リンクはアフィリエイトリンクを含みます
        </p>
      </CardContent>
    </Card>
  );
}

interface ProductCardProps {
  product: CategoryProducts["products"][number];
}

function ProductCard({ product }: ProductCardProps) {
  const rakutenUrl = buildRakutenSearchUrl(product.rakutenKeyword);
  const amazonUrl = buildAmazonSearchUrl(product.amazonKeyword);

  // どちらのリンクもない場合は表示しない
  if (!rakutenUrl && !amazonUrl) {
    return null;
  }

  return (
    <div className="rounded-lg border border-border bg-card/50 p-4">
      <h4 className="font-medium text-foreground">{product.name}</h4>
      <p className="mt-1 text-sm text-muted-foreground">{product.description}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {rakutenUrl && (
          <a
            href={rakutenUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-red-700"
          >
            <ExternalLink className="h-3 w-3" />
            楽天で探す
          </a>
        )}
        {amazonUrl && (
          <a
            href={amazonUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 rounded-md bg-orange-500 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-orange-600"
          >
            <ExternalLink className="h-3 w-3" />
            Amazonで探す
          </a>
        )}
      </div>
    </div>
  );
}
