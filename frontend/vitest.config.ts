import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import path from "node:path";

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    css: true,
    environmentOptions: {
      jsdom: {
        url: "http://localhost",
      },
    },
    sequence: {
      concurrent: false,
    },
    poolOptions: {
      threads: {
        minThreads: 1,
        maxThreads: 1,
      },
    },
  },
  resolve: {
    alias: [
      { find: "@/components/ui", replacement: path.resolve(__dirname, "./components/ui") },
      { find: "@/components/gym", replacement: path.resolve(__dirname, "./components/gym") },
      {
        find: "@/components/health-check-card",
        replacement: path.resolve(__dirname, "./components/health-check-card.tsx"),
      },
      { find: "@", replacement: path.resolve(__dirname, "./src") },
    ],
  },
});
