"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Equipment, getEquipments } from "@/lib/api";
import EquipmentSuggestInput from "@/components/EquipmentSuggestInput";
import GymSuggestInput from "@/components/GymSuggestInput";

type FormState = {
  pref: string;
  city: string;
  equipments: string[];
  sort: string;
  per_page: string;
};

function parseList(v: string | null): string[] {
  if (!v) return [];
  return v
    .split(",")
    .map(s => s.trim())
    .filter(Boolean);
}

export default function SearchForm() {
  const { data: equipments, isLoading } = useQuery({
    queryKey: ["equipments"],
    queryFn: getEquipments,
  });

  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const initial = useMemo<FormState>(
    () => ({
      pref: searchParams.get("pref") || "",
      city: searchParams.get("city") || "",
      equipments: parseList(searchParams.get("equipments")),
      sort: searchParams.get("sort") || "",
      per_page: searchParams.get("per_page") || "10",
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const [form, setForm] = useState<FormState>(initial);

  // Keep state in sync when URL changes via navigation
  useEffect(() => {
    setForm({
      pref: searchParams.get("pref") || "",
      city: searchParams.get("city") || "",
      equipments: parseList(searchParams.get("equipments")),
      sort: searchParams.get("sort") || "",
      per_page: searchParams.get("per_page") || "10",
    });
  }, [searchParams]);

  const updateQuery = (patch: Record<string, string | string[] | undefined>) => {
    const q = new URLSearchParams(searchParams.toString());
    Object.entries(patch).forEach(([k, v]) => {
      if (v === undefined || v === "") {
        q.delete(k);
      } else if (Array.isArray(v)) {
        if (v.length === 0) q.delete(k);
        else q.set(k, v.join(","));
      } else {
        q.set(k, v);
      }
    });
    // reset page on new search
    q.delete("page_token");
    router.push(`${pathname}?${q.toString()}`);
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Backend requires lower-case slug-like strings for pref/city
    const pref = form.pref.trim().toLowerCase();
    const city = form.city.trim().toLowerCase();
    updateQuery({
      pref,
      city,
      equipments: form.equipments,
      sort: form.sort,
      per_page: form.per_page,
    });
  };

  const clear = () => {
    setForm({ pref: "", city: "", equipments: [], sort: "", per_page: "10" });
    router.push(pathname);
  };

  return (
    <form className="stack card" onSubmit={onSubmit}>
      <h2>検索</h2>
      <div className="row">
        <label>
          Pref:
          <input
            type="text"
            value={form.pref}
            onChange={e => setForm(s => ({ ...s, pref: e.target.value }))}
            placeholder="例: 東京都"
          />
        </label>
        <label>
          City:
          <input
            type="text"
            value={form.city}
            onChange={e => setForm(s => ({ ...s, city: e.target.value }))}
            placeholder="例: 渋谷区"
          />
        </label>
        <GymSuggestInput
          pref={form.pref || undefined}
          onPickCity={(pref, city) => setForm(s => ({ ...s, pref: pref ?? "", city: city ?? "" }))}
        />
        <label>
          Sort:
          <select value={form.sort} onChange={e => setForm(s => ({ ...s, sort: e.target.value }))}>
            {/* Backend supports: freshness | richness | gym_name | created_at | score */}
            <option value="">Default (score)</option>
            <option value="score">Score</option>
            <option value="freshness">Freshness</option>
            <option value="richness">Richness</option>
            <option value="gym_name">Gym name</option>
            <option value="created_at">Created at</option>
          </select>
        </label>
        <label>
          Per page:
          <select
            value={form.per_page}
            onChange={e => setForm(s => ({ ...s, per_page: e.target.value }))}
          >
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
          </select>
        </label>
      </div>

      <fieldset>
        <legend>Equipments</legend>
        {equipments && (
          <EquipmentSuggestInput
            selected={(form.equipments
              .map(slug => equipments.find((m: Equipment) => m.slug === slug)?.name)
              .filter(Boolean) as string[])}
            onSelect={names => {
              // Map suggestion names to slugs using the loaded equipment master
              const master = equipments ?? [];
              const slugSet = new Set<string>(form.equipments);
              names.forEach(name => {
                const hit = master.find((m: Equipment) => (m.name ?? "").trim() === name.trim());
                if (hit?.slug) slugSet.add(hit.slug);
              });
              setForm(s => ({ ...s, equipments: Array.from(slugSet) }));
            }}
          />
        )}
        {isLoading && <div className="muted">Loading equipments...</div>}
        {!isLoading && equipments && equipments.length === 0 && (
          <div className="muted">No equipments</div>
        )}
        {!isLoading && equipments && equipments.length > 0 && (
          <div className="row" style={{ alignItems: "flex-start" }}>
            {equipments.map((e: Equipment) => {
              const key = e.slug ?? String(e.id ?? "");
              const name = e.name ?? key;
              const checked = form.equipments.includes(key);
              return (
                <label key={key} className="row" style={{ gap: 4 }}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={ev => {
                      const next = new Set(form.equipments);
                      if (ev.target.checked) next.add(key);
                      else next.delete(key);
                      setForm(s => ({ ...s, equipments: Array.from(next) }));
                    }}
                  />
                  <span>{name}</span>
                </label>
              );
            })}
          </div>
        )}
      </fieldset>

      <div className="row">
        <button className="btn" type="submit">
          検索
        </button>
        <button className="btn secondary" type="button" onClick={clear}>
          クリア
        </button>
      </div>
    </form>
  );
}
