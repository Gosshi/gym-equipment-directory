"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { getGymBySlug } from "@/lib/api";

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

  return (
    <div className="stack">
      <h1>{title}</h1>
      {data.address && <div className="muted">{data.address}</div>}
      {data.description && <p>{data.description}</p>}

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
