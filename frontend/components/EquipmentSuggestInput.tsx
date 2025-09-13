"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { suggestEquipments } from "@/lib/api";

type Props = {
  selected: string[];
  onSelect: (nextSelected: string[]) => void;
};

export default function EquipmentSuggestInput({ selected, onSelect }: Props) {
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
    queryKey: ["suggest", "equipments", debounced],
    queryFn: () => suggestEquipments(debounced, 8),
    enabled: debounced.length > 0,
  });

  const suggestions = useMemo(() => (data ?? []).filter(name => !selected.includes(name)), [data, selected]);

  const add = (name: string) => {
    const next = Array.from(new Set([...selected, name]));
    onSelect(next);
    setQ("");
    setOpen(false);
  };

  const remove = (name: string) => {
    const next = selected.filter(x => x !== name);
    onSelect(next);
  };

  return (
    <div style={{ position: "relative", minWidth: 280 }}>
      <label style={{ width: "100%" }}>
        Equipment サジェスト:
        <input
          type="text"
          value={q}
          onChange={e => setQ(e.target.value)}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
          placeholder="例: スクワット、ダンベル…"
          aria-expanded={open}
          aria-controls="equip-suggest-list"
          aria-autocomplete="list"
        />
      </label>
      {open && suggestions.length > 0 && (
        <ul id="equip-suggest-list" role="listbox" className="card" style={{ position: "absolute", zIndex: 10, width: "100%", marginTop: 4, listStyle: "none", padding: 0 }}>
          {suggestions.map((name, i) => (
            <li key={`${name}-${i}`}>
              <button className="btn secondary" type="button" onClick={() => add(name)} aria-label={`${name} を追加`} style={{ width: "100%", justifyContent: "flex-start" }}>
                {name}
              </button>
            </li>
          ))}
        </ul>
      )}
      {selected.length > 0 && (
        <div className="row" style={{ marginTop: 8 }}>
          {selected.map(name => (
            <span key={name} className="muted" style={{ border: "1px solid #e5e7eb", borderRadius: 999, padding: "2px 6px" }}>
              {name}
              <button type="button" aria-label={`${name} を削除`} onClick={() => remove(name)} style={{ marginLeft: 6, border: 0, background: "transparent", cursor: "pointer" }}>
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

