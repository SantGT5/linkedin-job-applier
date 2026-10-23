import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    // `npm run dev` against a running `make up` stack.
    proxy: {
      "/api": { target: "http://localhost:8080", changeOrigin: false },
      "/novnc": { target: "http://localhost:8080", ws: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
