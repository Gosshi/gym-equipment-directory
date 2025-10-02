"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function AdminLoginPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = token.trim();
    if (!trimmed) {
      setError("トークンを入力してください");
      return;
    }
    const expires = new Date();
    expires.setDate(expires.getDate() + 7);
    document.cookie = `admin_token=${encodeURIComponent(trimmed)}; path=/; max-age=${7 * 24 * 60 * 60}`;
    setError(null);
    router.push("/admin/candidates");
    router.refresh();
  };

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col justify-center gap-6 p-6">
      <h1 className="text-2xl font-semibold">Admin Login</h1>
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-4 rounded-md border border-gray-200 p-6 shadow-sm"
      >
        <label className="flex flex-col gap-2">
          <span className="text-sm font-medium text-gray-700">アクセス用トークン</span>
          <input
            type="password"
            className="rounded border border-gray-300 px-3 py-2"
            value={token}
            onChange={event => setToken(event.target.value)}
            placeholder="ADMIN_UI_TOKEN"
            autoFocus
          />
        </label>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <button
          type="submit"
          className="rounded bg-black px-4 py-2 text-white transition hover:bg-gray-800"
        >
          ログイン
        </button>
      </form>
      <p className="text-sm text-gray-600">
        .env に設定された <code>ADMIN_UI_TOKEN</code> と一致する値を入力してください。
      </p>
    </div>
  );
}
