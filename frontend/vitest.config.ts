import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";
export default defineConfig({
  resolve: { alias: { "@": fileURLToPath(new URL(".", import.meta.url)) } },
  esbuild: { jsx: "automatic" },
  test: {
    environment: "node",
    environmentMatchGlobs: [["**/*.dom.test.tsx", "jsdom"]],
    setupFiles: [],
    exclude: ["**/node_modules/**", "**/.next/**", "e2e/**"]
  }
});
