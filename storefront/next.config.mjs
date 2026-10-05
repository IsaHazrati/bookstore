import { fileURLToPath } from "node:url";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // خروجی مستقل برای ایمیج کوچک Docker
  output: "standalone",
  // کش محدود در حافظه به‌جای نوشتن نامحدود روی دیسک (cache-handler.js را ببین)
  cacheHandler: fileURLToPath(new URL("./cache-handler.js", import.meta.url)),
  cacheMaxMemorySize: 0, // کش داخلی Next خاموش؛ فقط handler بالا
};

export default nextConfig;
