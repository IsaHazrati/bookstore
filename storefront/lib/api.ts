// همه‌ی فراخوانی‌ها سمت سرور انجام می‌شوند (داخل شبکه‌ی Docker)، نه مرورگر.
const API = process.env.API_INTERNAL_URL ?? "http://backend:8000";
export const SITE_URL = (process.env.SITE_URL ?? "http://bookstore.localhost").replace(/\/$/, "");

export type BookType = "physical" | "digital" | "both";

export interface Category {
  id: number;
  name: string;
  slug: string;
}

export interface Book {
  id: number;
  title: string;
  slug: string;
  author: string;
  publisher: string | null;
  isbn: string | null;
  description: string;
  cover_image_url: string | null;
  published_date: string | null;
  book_type: BookType;
  price: string;
  in_stock: boolean;
  has_digital: boolean;
  category: Category | null;
}

export interface BookPage {
  items: Book[];
  total: number;
  page: number;
  page_size: number;
}

export interface BookQuery {
  q?: string;
  category?: string;
  book_type?: string;
  sort?: string;
  page?: number;
  page_size?: number;
}

export class NotFoundError extends Error {}

async function get<T>(path: string, revalidate = 60): Promise<T> {
  const res = await fetch(`${API}/api/v1${path}`, { next: { revalidate } });
  if (res.status === 404) throw new NotFoundError(path);
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export const getCategories = () => get<Category[]>("/categories");

export function getBooks(query: BookQuery = {}): Promise<BookPage> {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== "") p.set(k, String(v));
  return get<BookPage>(`/books?${p}`);
}

export const getBook = (slug: string) => get<Book>(`/books/${encodeURIComponent(slug)}`);

/** آدرس مطلق (برای OG و JSON-LD). مسیرهای نسبی مثل /media/... را به دامنه‌ی سایت وصل می‌کند. */
export const absolute = (path: string | null): string | undefined =>
  path ? (path.startsWith("http") ? path : `${SITE_URL}${path}`) : undefined;
