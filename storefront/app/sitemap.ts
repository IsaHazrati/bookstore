import type { MetadataRoute } from "next";
import { SITE_URL, getBooks, getCategories, type Book } from "@/lib/api";

// در زمان build بک‌اند در دسترس نیست؛ sitemap هر درخواست (با کش API) ساخته می‌شود.
export const dynamic = "force-dynamic";

const url = (path: string) => `${SITE_URL}${path}`;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const categories = await getCategories();

  const books: Book[] = [];
  for (let page = 1; ; page++) {
    const data = await getBooks({ page, page_size: 100 });
    books.push(...data.items);
    if (books.length >= data.total || data.items.length === 0) break;
  }

  return [
    { url: url("/"), changeFrequency: "daily", priority: 1 },
    { url: url("/books"), changeFrequency: "daily", priority: 0.8 },
    ...categories.map((c) => ({
      url: url(`/categories/${encodeURIComponent(c.slug)}`),
      changeFrequency: "daily" as const,
      priority: 0.7,
    })),
    ...books.map((b) => ({
      url: url(`/books/${encodeURIComponent(b.slug)}`),
      changeFrequency: "weekly" as const,
      priority: 0.6,
    })),
  ];
}
