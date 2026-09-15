import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "/app/",
  build: {
    outDir: "dist/client",
  },
  optimizeDeps: {
    include: ["react", "react-dom/client"],
  },
  plugins: [react(), tailwindcss()],
  server: {
    host: "0.0.0.0",
    allowedHosts: ["terminal.local"],
    proxy: {
      "/dashboard": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/reports": "http://127.0.0.1:8000",
    },
    warmup: {
      clientFiles: ["./src/main.tsx"],
    },
  },
  test: {
    environment: "jsdom",
    exclude: ["tests/**", "node_modules/**", "dist/**"],
    setupFiles: "./src/test/setup.ts",
  },
});
