export type HistoryNavigationMode = "push" | "replace";

export interface PlanNavigationOptions {
  pathname: string | null;
  currentSearch: string;
  nextSearch: string;
  mode: HistoryNavigationMode;
}

export interface NavigationPlan {
  url: string | null;
  mode: HistoryNavigationMode;
  shouldNavigate: boolean;
}

export const planNavigation = ({
  pathname,
  currentSearch,
  nextSearch,
  mode,
}: PlanNavigationOptions): NavigationPlan => {
  const normalizedMode: HistoryNavigationMode =
    mode === "push" && nextSearch === currentSearch ? "replace" : mode;

  if (!pathname) {
    return { url: null, mode: normalizedMode, shouldNavigate: false };
  }

  const url = nextSearch ? `${pathname}?${nextSearch}` : pathname;
  const shouldNavigate = !(normalizedMode === "replace" && nextSearch === currentSearch);

  return {
    url,
    mode: normalizedMode,
    shouldNavigate,
  };
};
