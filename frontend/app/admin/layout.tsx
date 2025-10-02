import type { ReactNode } from "react";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <div className="mx-auto w-full max-w-6xl p-6">{children}</div>;
}
