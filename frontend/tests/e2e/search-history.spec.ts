import { expect, test } from "@playwright/test";

// 安定性重視: pref=tokyo 選択後のページングと履歴遷移のみを最小検証
test.describe("検索条件の履歴ナビゲーション", () => {
  test("pref=tokyo の 1→2→3 ページ遷移と戻る/進む履歴", async ({ page }) => {
    const buildMeta = (p: number, total: number, hasNext: boolean, perPage = 2) => ({
      total,
      page: p,
      perPage,
      hasNext,
      hasPrev: p > 1,
      hasMore: hasNext,
      pageToken: hasNext ? String(p + 1) : null,
    });

    const baseResults = {
      items: [
        { id: 1, slug: "national-gym", name: "ナショナルジム" },
        { id: 2, slug: "coastal-fitness", name: "コースタルフィットネス" },
      ],
      meta: buildMeta(1, 2, false),
    };

    const tokyoPages = [
      {
        items: [
          { id: 11, slug: "tokyo-strong", name: "トーキョーストロング" },
          { id: 12, slug: "shibuya-fitness", name: "シブヤフィットネス" },
        ],
        meta: buildMeta(1, 6, true),
      },
      {
        items: [
          { id: 13, slug: "meguro-wellness", name: "メグロウェルネス" },
          { id: 14, slug: "akasaka-gym", name: "アカサカジム" },
        ],
        meta: buildMeta(2, 6, true),
      },
      {
        items: [
          { id: 15, slug: "ochanomizu-strong", name: "オチャノミズストロング" },
          { id: 16, slug: "ikebukuro-fit", name: "イケブクロフィット" },
        ],
        meta: buildMeta(3, 6, false),
      },
    ];

    // --- ルートモック ---
    await page.route("**/meta/prefectures", async route => {
      // デバッグ用にログ
      // eslint-disable-next-line no-console
      console.log("[mock] /meta/prefectures");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(["tokyo", "kanagawa"]),
      });
    });
    await page.route("**/meta/equipment-categories", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });
    await page.route("**/meta/cities**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });
    await page.route("**/suggest/gyms**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });
    await page.route("**/gyms/search**", async route => {
      const url = new URL(route.request().url());
      const pref = url.searchParams.get("pref");
      const pageParam = Number.parseInt(url.searchParams.get("page") ?? "1", 10);
      const p = Number.isFinite(pageParam) && pageParam > 0 ? pageParam : 1;
      let response;
      if (pref === "tokyo") {
        const clamped = Math.min(Math.max(p, 1), tokyoPages.length);
        response = tokyoPages[clamped - 1];
      } else {
        response = baseResults;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: response.items.map(g => ({
            id: g.id,
            slug: g.slug,
            name: g.name,
            city: "",
            prefecture: pref === "tokyo" ? "東京都" : "神奈川県",
            equipments: [],
            thumbnailUrl: null,
            score: 4.0,
            lastVerifiedAt: "2024-01-01T00:00:00Z",
          })),
          meta: response.meta,
        }),
      });
    });

    // --- 初期ページ ---
    await page.goto("/gyms");
    await page.waitForResponse(r => r.url().includes("/gyms/search") && !/pref=/.test(r.url()));

    const prefectureSelect = page.getByLabel("都道府県");
    const resultsSection = page.locator("section[aria-labelledby='gym-search-results-heading']");
    await expect(prefectureSelect).toHaveValue("");
    await expect(resultsSection.getByRole("heading", { level: 3 }).first()).toHaveText(
      "ナショナルジム",
    );

    // --- pref=tokyo 適用 (page=1) ---
    // option DOM 挿入をポーリングで待機 (visibility 不要)
    await page.waitForSelector("select#gym-search-prefecture");
    await page.waitForFunction(() => {
      const sel = document.querySelector(
        "select#gym-search-prefecture",
      ) as HTMLSelectElement | null;
      return !!sel && Array.from(sel.options).some(o => o.value === "tokyo");
    });
    const searchResp1 = page.waitForResponse(
      r => r.url().includes("/gyms/search") && /pref=tokyo/.test(r.url()),
    );
    await prefectureSelect.selectOption({ value: "tokyo" });
    await searchResp1;
    await expect(page).toHaveURL(/pref=tokyo/);
    await expect(resultsSection.getByRole("heading", { level: 3 }).first()).toHaveText(
      "トーキョーストロング",
    );

    // --- page=2 ---
    const nextButton1 = page.getByRole("button", { name: "次のページ" }).first();
    await expect(nextButton1).toBeVisible();
    await Promise.all([
      page.waitForResponse(
        r =>
          r.url().includes("/gyms/search") && /pref=tokyo/.test(r.url()) && /page=2/.test(r.url()),
      ),
      nextButton1.click(),
    ]);
    await expect(page).toHaveURL(/pref=tokyo.*page=2/);
    await expect(resultsSection.getByRole("heading", { level: 3 }).first()).toHaveText(
      "メグロウェルネス",
    );

    // --- page=3 ---
    const nextButton2 = page.getByRole("button", { name: "次のページ" }).first();
    await expect(nextButton2).toBeVisible();
    await Promise.all([
      page.waitForResponse(
        r =>
          r.url().includes("/gyms/search") && /pref=tokyo/.test(r.url()) && /page=3/.test(r.url()),
      ),
      nextButton2.click(),
    ]);
    await expect(page).toHaveURL(/pref=tokyo.*page=3/);
    await expect(resultsSection.getByRole("heading", { level: 3 }).first()).toHaveText(
      "オチャノミズストロング",
    );
    await expect(page.getByRole("button", { name: "次のページ" })).toBeDisabled();

    // --- 履歴: 3 -> 2 -> 1(=page param 無し) -> forward ---
    await page.goBack();
    await expect(page).toHaveURL(/pref=tokyo.*page=2/);
    await page.goBack();
    // page=1 の表現: page パラメータ無しを期待（実装差異で page=1 が付く場合は緩和しても良い）
    await expect(page).not.toHaveURL(/page=2|page=3/);
    await expect(page).toHaveURL(/pref=tokyo/);
    await page.goForward();
    await expect(page).toHaveURL(/pref=tokyo.*page=2/);
    await page.goForward();
    await expect(page).toHaveURL(/pref=tokyo.*page=3/);
  });
});
