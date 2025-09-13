"use client";

import Link from "next/link";
import FavoriteButton from "@/components/FavoriteButton";

type Props = {
  gyms: any[] | undefined;
  isLoading: boolean;
  isError: boolean;
  error?: unknown;
  nextPageToken?: string | null;
  onNextPage?: (token: string) => void;
};

function EquipmentChips({ list }: { list?: unknown }) {
  const items: string[] = Array.isArray(list)
    ? (list as any[]).map(x => {
        if (typeof x === "string") return x;
        if (x && typeof x === "object") {
          return (x as any).name ?? (x as any).slug ?? "";
        }
        return "";
      })
    : [];
  return (
    <div className="row" style={{ gap: 6 }}>
      {items.filter(Boolean).map((name, i) => (
        <span
          key={`${name}-${i}`}
          className="muted"
          style={{ border: "1px solid #e5e7eb", borderRadius: 999, padding: "2px 8px" }}
        >
          {name}
        </span>
      ))}
    </div>
  );
}

export default function GymList({
  gyms,
  isLoading,
  isError,
  error,
  nextPageToken,
  onNextPage,
}: Props) {
  if (isLoading) return <div className="card">Loading gyms...</div>;
  if (isError) return <div className="card">Error: {String(error)}</div>;
  const list = gyms ?? [];
  if (list.length === 0) return <div className="card">No gyms found.</div>;

  return (
    <div className="stack">
      {list.map((g: any) => {
        const slug = g.slug ?? g.id ?? "";
        const title = g.name ?? g.title ?? slug;
        return (
          <div key={slug} className="card stack">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div>
                <h3 style={{ marginBottom: 4 }}>
                  <Link href={`/gyms/${encodeURIComponent(slug)}`}>{title}</Link>
                </h3>
                {g.address && <div className="muted">{g.address}</div>}
              </div>
              {typeof g.id === "number" && (
                <div>
                  <FavoriteButton gymId={g.id} gymSlug={g.slug ?? String(g.id)} compact />
                </div>
              )}
            </div>
            <EquipmentChips list={g.equipments} />
          </div>
        );
      })}

      <div className="row" style={{ justifyContent: "space-between" }}>
        <div />
        <div className="row">
          {nextPageToken && onNextPage && (
            <button className="btn" onClick={() => onNextPage(nextPageToken)}>
              次のページ
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
