import { http, HttpResponse } from "msw";

const prefectureSlugs = ["tokyo", "kanagawa"];
const equipmentOptions = [
  { slug: "squat-rack", name: "スクワットラック", category: "free_weight" },
  { slug: "smith-machine", name: "スミスマシン", category: "strength" },
  { slug: "treadmill", name: "トレッドミル", category: "cardio" },
];

const tokyoCities = [
  { city: "shinjuku", count: 12 },
  { city: "shibuya", count: 9 },
  { city: "meguro", count: 5 },
];

export const defaultGymSearchResponse = {
  items: [
    {
      id: 1,
      slug: "tokyo-fit",
      name: "東京フィットジム",
      city: "shinjuku",
      pref: "tokyo",
      equipments: ["ダンベル", "パワーラック"],
      thumbnail_url: null,
      last_verified_at: "2024-02-10T09:00:00Z",
    },
    {
      id: 2,
      slug: "shibuya-strength",
      name: "渋谷ストレングス",
      city: "shibuya",
      pref: "tokyo",
      equipments: ["マシン", "フリーウェイト"],
      thumbnail_url: null,
      last_verified_at: "2024-03-05T15:30:00Z",
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
  per_page: 20,
  has_next: false,
  has_prev: false,
  has_more: false,
  page_token: null,
};

export const handlers = [
  http.get("*/meta/prefectures", () => HttpResponse.json(prefectureSlugs)),
  http.get("*/meta/equipments", () => HttpResponse.json(equipmentOptions)),
  http.get("*/meta/cities", ({ request }) => {
    const url = new URL(request.url);
    const pref = url.searchParams.get("pref");
    if (pref === "tokyo") {
      return HttpResponse.json(tokyoCities);
    }
    return HttpResponse.json([]);
  }),
  http.get("*/suggest/gyms", () => HttpResponse.json([])),
  http.get("*/gyms/search", () => HttpResponse.json(defaultGymSearchResponse)),
  http.get("*/me/favorites", () => HttpResponse.json([])),
  http.get("*/me/history", () => HttpResponse.json({ items: [] })),
];
