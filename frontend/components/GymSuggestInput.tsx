"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { GymSuggestItem, suggestGyms } from "@/lib/api";
import Link from "next/link";

type Props = {
  pref?: string;
  onPickCity?: (pref: string | undefined, city: string | undefined) => void;
};

export default function GymSuggestInput({ pref, onPickCity }: Props) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const timer = useRef<number | null>(null);
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setDebounced(q.trim()), 300);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [q]);

  const { data } = useQuery({
    queryKey: ["suggest", "gyms", pref ?? null, debounced],
    queryFn: () => suggestGyms(debounced, pref || undefined, 10),
    enabled: debounced.length > 0,
  });

  const suggestions = useMemo(() => (data ?? []) as GymSuggestItem[], [data]);

  const pickCity = (it: GymSuggestItem) => {
    if (onPickCity) onPickCity(it.pref ?? undefined, it.city ?? undefined);
    setQ("");
    setOpen(false);
  };

  return (
    <div style={{ position: "relative", minWidth: 320 }}>
      <label style={{ width: "100%" }}>
        Gym/地名 サジェスト:
        <input
          type="text"
          value={q}
          onChange={e => setQ(e.target.value)}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
          placeholder="ジム名や地名を入力…"
          aria-expanded={open}
          aria-controls="gym-suggest-list"
          aria-autocomplete="list"
        />
      </label>
      {open && suggestions.length > 0 && (
        <ul id="gym-suggest-list" role="listbox" className="card" style={{ position: "absolute", zIndex: 10, width: "100%", marginTop: 4, listStyle: "none", padding: 0 }}>
          {suggestions.map((it, i) => (
            <li key={`${it.slug}-${i}`} className="row" style={{ padding: 4, justifyContent: "space-between" }}>
              <Link className="btn" href={`/gyms/${encodeURIComponent(it.slug)}`} aria-label={`${it.name} 詳細へ`}>
                {it.name}
              </Link>
              <button
                type="button"
                className="btn secondary"
                onClick={() => pickCity(it)}
                aria-label={`検索条件に ${it.pref ?? ""} ${it.city ?? ""} をセット`}
              >
                条件にセット
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

