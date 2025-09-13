"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { getGymBySlug } from "@/lib/api";
import FavoriteButton from "@/components/FavoriteButton";
import { useMemo, useState } from "react";

export default function GymDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["gym", slug],
    queryFn: () => getGymBySlug(slug),
    enabled: !!slug,
  });

  if (isLoading) return <div className="card">Loading...</div>;
  if (isError) return <div className="card">Error: {String(error)}</div>;
  if (!data) return <div className="card">Not found</div>;

  const title = data.name ?? data.slug;
  const eq: any[] = Array.isArray((data as any).equipments)
    ? ((data as any).equipments as any[])
    : [];
  const images: { url: string; source?: string | null }[] = Array.isArray((data as any).images)
    ? ((data as any).images as any[]).map((im: any) => ({ url: im?.url, source: im?.source }))
    : [];
  const gymId = (data as any).id as number | undefined;
  const [idx, setIdx] = useState(0);
  const hasImages = images.length > 0;
  const current = useMemo(() => (hasImages ? images[idx % images.length] : null), [images, idx, hasImages]);

  return (
    <div className="stack">
      <h1>{title}</h1>
      {data.address && <div className="muted">{data.address}</div>}
      {data.description && <p>{data.description}</p>}

      {hasImages && (
        <div className="card stack" aria-label="画像スライダー">
          {current && (
            <img
              src={current.url}
              alt={title}
              style={{ width: "100%", maxHeight: 360, objectFit: "cover", borderRadius: 8 }}
            />
          )}
          <div className="row" style={{ justifyContent: "space-between" }}>
            <button className="btn secondary" type="button" onClick={() => setIdx(i => (i - 1 + images.length) % images.length)} aria-label="前の画像">
              ‹
            </button>
            <div className="muted">{idx + 1} / {images.length}</div>
            <button className="btn secondary" type="button" onClick={() => setIdx(i => (i + 1) % images.length)} aria-label="次の画像">
              ›
            </button>
          </div>
        </div>
      )}

      {typeof gymId === "number" && (
        <div>
          <FavoriteButton gymId={gymId} gymSlug={data.slug} />
        </div>
      )}

      <div className="card stack">
        <h2>装備</h2>
        {eq.length === 0 && <div className="muted">No equipments listed.</div>}
        {eq.length > 0 && (
          <ul style={{ paddingLeft: 18, margin: 0 }}>
            {eq.map((e, i) => (
              <li key={i}>{e?.name ?? e?.slug ?? String(e)}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
