"use client";

import { useEffect, useRef } from "react";

import { buildSearchQueryString, gymSearchStore } from "@/store/searchStore";

const isBrowser = () => typeof window !== "undefined";

export function useUrlSync() {
  const skipSyncRef = useRef(false);
  const lastQueryRef = useRef<string>("");

  useEffect(() => {
    if (!isBrowser()) {
      return;
    }

    const initialUrl = new URL(window.location.href);
    const { hydrateFromUrl } = gymSearchStore.getState();
    hydrateFromUrl(initialUrl);
    lastQueryRef.current = initialUrl.searchParams.toString();

    const handlePopstate = () => {
      skipSyncRef.current = true;
      const currentUrl = new URL(window.location.href);
      gymSearchStore.getState().applyUrlState(currentUrl);
      lastQueryRef.current = currentUrl.searchParams.toString();
      skipSyncRef.current = false;
    };

    window.addEventListener("popstate", handlePopstate);

    return () => {
      window.removeEventListener("popstate", handlePopstate);
    };
  }, []);

  useEffect(() => {
    if (!isBrowser()) {
      return;
    }

    return gymSearchStore.subscribe(
      state => ({
        hydrated: state.hydrated,
        query: buildSearchQueryString(state),
        pendingHistory: state.pendingHistory,
      }),
      snapshot => {
        if (!snapshot.hydrated) {
          return;
        }
        if (skipSyncRef.current) {
          return;
        }
        const pathname = window.location.pathname;
        const query = snapshot.query;
        if (query === lastQueryRef.current) {
          return;
        }
        const url = query ? `${pathname}?${query}` : pathname;
        if (snapshot.pendingHistory === "push") {
          window.history.pushState(null, "", url);
        } else {
          window.history.replaceState(null, "", url);
        }
        lastQueryRef.current = query;
        gymSearchStore.getState().markUrlSynced(query);
      },
    );
  }, []);
}
