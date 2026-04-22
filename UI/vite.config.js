// Created by Metrum AI for AMD

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/backend": {
        target: process.env.VITE_API_TARGET || "http://localhost:8001",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/backend/, ""),
      },
      "/metrics": {
        target: process.env.VITE_PROM_TARGET || "http://localhost:9091",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/metrics/, ""),
      },
    },
  },
});
