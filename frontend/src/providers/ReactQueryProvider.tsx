"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

const createClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        refetchOnMount: false,
        retry: 1,
        staleTime: 0,
        gcTime: 1000 * 60 * 5,
        meta: {
          persistErrors: true,
        },
      },
    },
  });

interface ReactQueryProviderProps {
  children: ReactNode;
}

export function ReactQueryProvider({ children }: ReactQueryProviderProps) {
  const [client] = useState(createClient);

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
