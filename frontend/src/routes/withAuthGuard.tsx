"use client";

import { useCallback } from "react";

import { useAuth } from "@/auth/AuthProvider";

export function useAuthGuard<T extends (...args: any[]) => unknown>(
  action: T,
): (...args: Parameters<T>) => Promise<Awaited<ReturnType<T>> | undefined> {
  const { user, requireAuth } = useAuth();

  return useCallback(
    async (...args: Parameters<T>) => {
      let ensuredUser = user;
      if (!ensuredUser) {
        try {
          ensuredUser = await requireAuth();
        } catch (error) {
          if (process.env.NODE_ENV !== "production") {
            // eslint-disable-next-line no-console
            console.debug("Authentication required action cancelled", error);
          }
          return undefined;
        }
      }

      return action(...args) as Awaited<ReturnType<T>>;
    },
    [action, requireAuth, user],
  );
}

export const withAuthGuard = useAuthGuard;
