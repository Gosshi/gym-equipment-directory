"use client";

import { useEffect, useMemo, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { GymEquipmentDetail } from "@/types/gym";

interface GymEquipmentTabsProps {
  equipments: GymEquipmentDetail[];
  className?: string;
}

const DEFAULT_CATEGORY = "その他";

const toCategoryKey = (label: string) => label.trim().toLowerCase();

export function GymEquipmentTabs({ equipments, className }: GymEquipmentTabsProps) {
  const items = useMemo(() => {
    if (!equipments) {
      return [] as GymEquipmentDetail[];
    }
    return equipments
      .map(equipment => ({
        ...equipment,
        name: equipment.name.trim(),
        category: equipment.category?.trim() ?? undefined,
        description: equipment.description?.trim() ?? undefined,
      }))
      .filter(equipment => equipment.name.length > 0);
  }, [equipments]);

  const categories = useMemo(() => {
    const map = new Map<string, { key: string; label: string; items: GymEquipmentDetail[] }>();
    items.forEach(item => {
      const label = item.category && item.category.length > 0 ? item.category : DEFAULT_CATEGORY;
      const key = toCategoryKey(label);
      if (!map.has(key)) {
        map.set(key, { key, label, items: [] });
      }
      map.get(key)!.items.push(item);
    });
    return Array.from(map.values());
  }, [items]);

  const [activeTab, setActiveTab] = useState<string>("all");

  useEffect(() => {
    setActiveTab("all");
  }, [items.length]);

  if (items.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>設備情報</CardTitle>
          <CardDescription>現在提供できる設備情報がありません。</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            設備の詳細情報が登録され次第、こちらに表示されます。
          </p>
        </CardContent>
      </Card>
    );
  }

  const allTabKey = "all";
  const tabItems = [
    { key: allTabKey, label: `全て (${items.length})` },
    ...categories.map(category => ({
      key: category.key,
      label: `${category.label} (${category.items.length})`,
    })),
  ];
  const activeTabLabel =
    tabItems.find(tab => tab.key === activeTab)?.label ?? tabItems[0]?.label ?? "全て";

  const activeItems =
    activeTab === allTabKey
      ? items
      : (categories.find(category => category.key === activeTab)?.items ?? items);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>設備</CardTitle>
        <CardDescription>カテゴリ別に施設の主要設備を確認できます。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="設備カテゴリ">
          {tabItems.map(tab => (
            <button
              key={tab.key}
              role="tab"
              aria-selected={activeTab === tab.key}
              className={cn(
                "rounded-full border px-3 py-1 text-sm transition",
                activeTab === tab.key
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-background text-muted-foreground hover:border-primary/60 hover:text-foreground",
              )}
              onClick={() => setActiveTab(tab.key)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div
          role="tabpanel"
          className="grid gap-3 md:grid-cols-2"
          aria-label={`${activeTabLabel}の設備リスト`}
        >
          {activeItems.map((equipment, index) => {
            const categoryLabel =
              equipment.category && equipment.category.length > 0
                ? equipment.category
                : DEFAULT_CATEGORY;
            const description = equipment.description ?? "詳細情報は準備中です。";
            const key = `${equipment.id ?? equipment.name}-${index}`;

            return (
              <div
                key={key}
                className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4 shadow-sm transition hover:shadow-md"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-base font-semibold text-foreground">{equipment.name}</h3>
                  <span className="inline-flex items-center rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground">
                    {categoryLabel}
                  </span>
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
