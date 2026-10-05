// کش ISR/داده‌ی Next.js در حافظه با سقف تعداد (LRU).
//
// پیش‌فرض Next هر صفحه‌ی ISR را روی دیسک می‌نویسد، حتی ۴۰۴ آدرس‌های تصادفی؛
// در بررسی کد ۳۰۰ درخواست به /books/<تصادفی> حدود ۹۰۰ فایل ساخت و بدون سقف رشد می‌کرد.
// اینجا قدیمی‌ترین ورودی‌ها حذف می‌شوند، پس حافظه و دیسک محدود می‌مانند.
// (با ری‌استارت کانتینر کش خالی می‌شود؛ صفحات در اولین بازدید دوباره ساخته می‌شوند.)

const MAX_ENTRIES = Number(process.env.NEXT_CACHE_MAX_ENTRIES) || 1000;
const cache = new Map();

module.exports = class LruCacheHandler {
  constructor(options) {
    this.options = options;
  }

  async get(key) {
    const entry = cache.get(key);
    if (entry === undefined) return null;
    // جابه‌جایی به انتهای Map = «اخیراً استفاده‌شده»
    cache.delete(key);
    cache.set(key, entry);
    return entry;
  }

  async set(key, data, ctx) {
    cache.delete(key);
    cache.set(key, { value: data, lastModified: Date.now(), tags: (ctx && ctx.tags) || [] });
    while (cache.size > MAX_ENTRIES) {
      cache.delete(cache.keys().next().value);
    }
  }

  async revalidateTag(tags) {
    const list = [tags].flat();
    for (const [key, entry] of cache) {
      if (entry.tags.some((t) => list.includes(t))) cache.delete(key);
    }
  }

  resetRequestCache() {}
};
