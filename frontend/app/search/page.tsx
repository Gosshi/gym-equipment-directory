"use client";

import { useQuery } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import SearchForm from "@/components/SearchForm";
import GymList from "@/components/GymList";
import { searchGyms } from "@/lib/api";

function useQueryParams() {
  const sp = useSearchParams();
  return useMemo(() => {
    const equipments = sp.get("equipments")
      ? sp.get("equipments")!.split(",").map((s) => s.trim()).filter(Boolean)
      : [];
    return {
      pref: sp.get("pref") || undefined,
      city: sp.get("city") || undefined,
      equipments,
      sort: sp.get("sort") || undefined,
      per_page: sp.get("per_page") ? Number(sp.get("per_page")) : undefined,
      page_token: sp.get("page_token") || undefined,
    };
  }, [sp]);
}

export default function SearchPage() {
  const params = useQueryParams();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["gyms", params],
    queryFn: () => searchGyms(params),
    enabled: true,
  });

  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();

  const nextPage = useCallback(
    (token: string) => {
      const q = new URLSearchParams(sp.toString());
      if (token) q.set("page_token", token);
      else q.delete("page_token");
      router.push(`${pathname}?${q.toString()}`);
    },
    [pathname, router, sp],
  );

  const gyms = data?.items ?? (data as any)?.gyms ?? [];
  const nextToken = (data as any)?.page_token ?? null;
  const hasNext = Boolean((data as any)?.has_next);

  return (
    <div className="stack">
      <h1>ジム検索</h1>
      <SearchForm />
      <GymList
        gyms={gyms}
        isLoading={isLoading}
        isError={isError}
        error={error as any}
        nextPageToken={hasNext ? nextToken : null}
        onNextPage={nextPage}
      />
    </div>
  );
}
