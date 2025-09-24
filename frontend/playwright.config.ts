import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30 * 1000,
  retries: 0,
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
      },
    },
  ],
});
