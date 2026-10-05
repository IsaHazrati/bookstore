// پارامترهای URL ورودی کاربر هستند؛ قبل از فرستادن به API اعتبارسنجی می‌شوند
// تا مقدار نامعتبر به‌جای خطای ۵۰۰ نادیده گرفته شود.
type Raw = Record<string, string | string[] | undefined>;

const SORTS = ["newest", "price_asc", "price_desc", "title"] as const;
const TYPES = ["physical", "digital"] as const;
const MAX_PAGE = 10_000;

const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) || undefined;

export interface ListParams {
  q?: string;
  category?: string;
  book_type?: string;
  sort?: string;
  page: number;
}

export function parseListParams(sp: Raw): ListParams {
  const q = first(sp.q)?.trim().slice(0, 100) || undefined;
  const sort = SORTS.find((s) => s === first(sp.sort));
  const book_type = TYPES.find((t) => t === first(sp.book_type));
  const n = Math.floor(Number(first(sp.page)));
  const page = Number.isFinite(n) ? Math.min(Math.max(n, 1), MAX_PAGE) : 1;
  return { q, category: first(sp.category)?.slice(0, 140), book_type, sort, page };
}
