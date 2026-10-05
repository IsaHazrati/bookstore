import type { Metadata } from "next";
import Link from "next/link";
import BookGrid from "@/components/BookGrid";
import Filters from "@/components/Filters";
import Pagination from "@/components/Pagination";
import { getBooks, getCategories } from "@/lib/api";
import { parseListParams } from "@/lib/params";

export const dynamic = "force-dynamic";
const PAGE_SIZE = 12;

type SP = Promise<Record<string, string | string[] | undefined>>;

export async function generateMetadata({ searchParams }: { searchParams: SP }): Promise<Metadata> {
  const { q, category, book_type, sort, page } = parseListParams(await searchParams);
  const filtered = Boolean(q || category || book_type || sort);
  return {
    title: "همه‌ی کتاب‌ها",
    description: "فهرست کتاب‌های چاپی و دیجیتال.",
    // نتایج فیلتر/جستجو محتوای تکراری‌اند؛ فقط لیست اصلی و صفحه‌بندی‌اش ایندکس شود
    robots: filtered ? { index: false, follow: true } : undefined,
    alternates: { canonical: page > 1 && !filtered ? `/books?page=${page}` : "/books" },
  };
}

export default async function BooksPage({ searchParams }: { searchParams: SP }) {
  const { q, category, book_type, sort, page } = parseListParams(await searchParams);

  const [data, categories] = await Promise.all([
    getBooks({ q, category, book_type, sort, page, page_size: PAGE_SIZE }),
    getCategories(),
  ]);
  const pages = Math.max(1, Math.ceil(data.total / data.page_size));

  const hrefFor = (p: number) => {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries({ q, category, book_type, sort })) if (v) params.set(k, v);
    if (p > 1) params.set("page", String(p));
    const s = params.toString();
    return s ? `/books?${s}` : "/books";
  };

  return (
    <>
      <h1>همه‌ی کتاب‌ها</h1>
      <ul className="cats" aria-label="دسته‌بندی‌ها">
        <li><Link href="/books" aria-current={!category ? "page" : undefined}>همه</Link></li>
        {categories.map((c) => (
          <li key={c.id}>
            <Link href={`/categories/${c.slug}`}>{c.name}</Link>
          </li>
        ))}
      </ul>
      <Filters categories={categories} q={q} category={category} bookType={book_type} sort={sort} action="/books" />
      <p className="muted">{data.total.toLocaleString("fa-IR")} کتاب</p>
      <BookGrid books={data.items} />
      <Pagination page={page} pages={pages} hrefFor={hrefFor} />
    </>
  );
}
