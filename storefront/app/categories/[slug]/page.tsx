import type { Metadata } from "next";
import { notFound } from "next/navigation";
import BookGrid from "@/components/BookGrid";
import Filters from "@/components/Filters";
import Pagination from "@/components/Pagination";
import { getBooks, getCategories } from "@/lib/api";
import { parseListParams } from "@/lib/params";

export const dynamic = "force-dynamic";
const PAGE_SIZE = 12;

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

async function findCategory(slug: string) {
  const decoded = decodeURIComponent(slug);
  return (await getCategories()).find((c) => c.slug === decoded);
}

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const { slug } = await params;
  const { q, book_type, sort, page } = parseListParams(await searchParams);
  const cat = await findCategory(slug);
  if (!cat) return { title: "دسته‌بندی پیدا نشد", robots: { index: false } };
  const filtered = Boolean(q || book_type || sort);
  const base = `/categories/${cat.slug}`;
  return {
    title: `کتاب‌های ${cat.name}`,
    description: `خرید آنلاین کتاب‌های دسته‌ی ${cat.name} (چاپی و دیجیتال).`,
    robots: filtered ? { index: false, follow: true } : undefined,
    alternates: { canonical: page > 1 && !filtered ? `${base}?page=${page}` : base },
  };
}

export default async function CategoryPage({ params, searchParams }: Props) {
  const { slug } = await params;
  const { q, book_type, sort, page } = parseListParams(await searchParams);
  const cat = await findCategory(slug);
  if (!cat) notFound();

  const [data, categories] = await Promise.all([
    getBooks({ category: cat.slug, q, book_type, sort, page, page_size: PAGE_SIZE }),
    getCategories(),
  ]);
  const pages = Math.max(1, Math.ceil(data.total / data.page_size));
  const hrefFor = (p: number) => {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries({ q, book_type, sort })) if (v) params.set(k, v);
    if (p > 1) params.set("page", String(p));
    const s = params.toString();
    return `/categories/${cat.slug}${s ? `?${s}` : ""}`;
  };

  return (
    <>
      <p className="crumbs"><a href="/books">کتاب‌ها</a> / {cat.name}</p>
      <h1>{cat.name}</h1>
      <Filters categories={categories} q={q} bookType={book_type} sort={sort} action={`/categories/${cat.slug}`} />
      <p className="muted">{data.total.toLocaleString("fa-IR")} کتاب</p>
      <BookGrid books={data.items} />
      <Pagination page={page} pages={pages} hrefFor={hrefFor} />
    </>
  );
}
