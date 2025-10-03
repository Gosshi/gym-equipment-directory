export type GymLite = {
  slug?: string | null;
  name?: string | null;
};

function isDevLike(): boolean {
  const env = process.env.NEXT_PUBLIC_APP_ENV?.toLowerCase();
  if (env) {
    return env === "dev" || env === "demo";
  }
  return process.env.NODE_ENV !== "production";
}

const isDummyGym = (gym: GymLite): boolean => {
  const slug = (gym.slug ?? "").toLowerCase();
  if (slug.startsWith("dummy-") || slug.startsWith("bulk-")) {
    return true;
  }

  const name = (gym.name ?? "").toString();
  if (name.startsWith("ダミー")) {
    return true;
  }

  return false;
};

/**
 * ダミーのジムデータを検索結果から除外する。
 *
 * dev / demo 環境のみ有効で、本番環境ではフィルタしない。
 */
export function filterOutDummyGyms<T extends GymLite>(gyms: T[]): T[] {
  if (!isDevLike()) {
    return gyms;
  }

  return gyms.filter(gym => !isDummyGym(gym));
}
