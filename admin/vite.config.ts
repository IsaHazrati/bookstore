import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // در حالت توسعه‌ی محلی (بدون Docker) درخواست‌های /api به بک‌اند می‌رود
    proxy: { "/api": "http://localhost:8000", "/media": "http://localhost:8000" },
  },
});
