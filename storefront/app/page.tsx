import Link from "next/link";
import BookGrid from "@/components/BookGrid";
import { getBooks, getCategories } from "@/lib/api";

// لیست‌ها هر درخواست رندر می‌شوند (داده‌ی API خودش ۶۰ ثانیه کش می‌شود)؛
// در زمان build بک‌اند در دسترس نیست، پس prerender نمی‌شوند.
export const dynamic = "force-dynamic";

export default async function Home() {
  const [latest, categories] = await Promise.all([getBooks({ sort: "newest", page_size: 8 }), getCategories()]);
  return (
    <>
      <h1>کتاب‌فروشی آنلاین</h1>
      <p className="muted">کتاب چاپی و نسخه‌ی دیجیتال، با تحویل سریع.</p>
      {categories.length > 0 && (
        <ul className="cats" aria-label="دسته‌بندی‌ها">
          {categories.map((c) => <li key={c.id}><Link href={`/categories/${c.slug}`}>{c.name}</Link></li>)}
        </ul>
      )}
      <h2>تازه‌ترین کتاب‌ها</h2>
      <BookGrid books={latest.items} />
      {latest.total > latest.items.length && <p><Link href="/books">مشاهده‌ی همه‌ی کتاب‌ها ←</Link></p>}
    </>
  );
}
