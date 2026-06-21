import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The dev server proxies /api to the local FastAPI backend (orionfold dev).
// Production build emits to dist/, which scripts/build.sh embeds into the wheel.
// Port and proxy target are env-overridable so a second checkout can run on
// free ports without colliding (VITE_DEV_PORT / VITE_API_PROXY).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: Number(process.env.VITE_DEV_PORT) || 5173,
    proxy: {
      "/api": process.env.VITE_API_PROXY || "http://127.0.0.1:8787",
    },
  },
  build: {
    outDir: "dist",
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/setupTests.ts"],
  },
});
