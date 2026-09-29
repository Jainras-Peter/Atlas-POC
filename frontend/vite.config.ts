import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        // Critical for SSE: do not buffer agent token / status events
        configure: (proxy) => {
          proxy.on("proxyRes", (proxyRes) => {
            const type = proxyRes.headers["content-type"] || "";
            if (String(type).includes("text/event-stream")) {
              proxyRes.headers["cache-control"] = "no-cache, no-transform";
              proxyRes.headers["x-accel-buffering"] = "no";
              // Prevent node-http-proxy from buffering the body
              proxyRes.headers["connection"] = "keep-alive";
            }
          });
        },
      },
    },
  },
});
