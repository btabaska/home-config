import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The SPA lives in web/ and is served static by the Node server in production.
// In dev, Vite serves it on :5173 and proxies /api to the Hono server on :8787.
export default defineConfig({
  root: "web",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8787",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "../dist",
    emptyOutDir: true,
  },
});
