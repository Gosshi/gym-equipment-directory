import { useCallback, useEffect, useRef, useState } from "react";

import { getGymBySlug } from "@/services/gyms";
import type { GymDetail } from "@/types/gym";

export interface UseGymDetailResult {
  data: GymDetail | null;
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

export function useGymDetail(slug: string | null): UseGymDetailResult {
  const [data, setData] = useState<GymDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const reload = useCallback(() => {
    if (slug) {
      setReloadToken(previous => previous + 1);
    }
  }, [slug]);

  useEffect(() => {
    if (!slug) {
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      setData(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current?.abort();
    abortControllerRef.current = controller;

    let isMounted = true;
    setIsLoading(true);
    setError(null);
    setData(null);

    void getGymBySlug(slug, { signal: controller.signal })
      .then(result => {
        if (!isMounted) {
          return;
        }
        setData(result);
      })
      .catch((thrownError: unknown) => {
        if (!isMounted || (thrownError instanceof Error && thrownError.name === "AbortError")) {
          return;
        }
        const message =
          thrownError instanceof Error && thrownError.message
            ? thrownError.message
            : "ジム詳細の取得に失敗しました。";
        setError(message);
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [slug, reloadToken]);

  return { data, isLoading, error, reload };
}
