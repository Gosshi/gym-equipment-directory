import { useMemo } from "react";

import type { GymSummary } from "@/types/gym";

export type SearchResultStatus = "loading" | "error" | "empty" | "success";

type UseSearchResultStateOptions = {
  isLoading: boolean;
  error: string | null;
  items: GymSummary[];
};

export function useSearchResultState({ isLoading, error, items }: UseSearchResultStateOptions) {
  return useMemo(() => {
    if (error) {
      return {
        status: "error" as SearchResultStatus,
        isError: true,
        isLoading: false,
        isEmpty: false,
        isSuccess: false,
      };
    }

    if (isLoading) {
      return {
        status: "loading" as SearchResultStatus,
        isError: false,
        isLoading: true,
        isEmpty: false,
        isSuccess: false,
      };
    }

    if (items.length === 0) {
      return {
        status: "empty" as SearchResultStatus,
        isError: false,
        isLoading: false,
        isEmpty: true,
        isSuccess: false,
      };
    }

    return {
      status: "success" as SearchResultStatus,
      isError: false,
      isLoading: false,
      isEmpty: false,
      isSuccess: true,
    };
  }, [error, isLoading, items.length]);
}
