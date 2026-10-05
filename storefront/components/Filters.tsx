import type { Category } from "@/lib/api";

/** فرم GET ساده: بدون JavaScript هم کار می‌کند. */
export default function Filters({
  categories, q, category, bookType, sort, action,
}: {
  categories: Category[]; q?: string; category?: string; bookType?: string; sort?: string; action: string;
}) {
  return (
    <form className="filters" action={action} method="get">
      <input type="search" name="q" defaultValue={q} placeholder="جستجوی عنوان یا نویسنده" maxLength={100} aria-label="جستجو" />
      {action === "/books" && (
        <select name="category" defaultValue={category ?? ""} aria-label="دسته‌بندی">
          <option value="">همه‌ی دسته‌ها</option>
          {categories.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
        </select>
      )}
      <select name="book_type" defaultValue={bookType ?? ""} aria-label="نوع کتاب">
        <option value="">چاپی و دیجیتال</option>
        <option value="physical">چاپی</option>
        <option value="digital">دیجیتال</option>
      </select>
      <select name="sort" defaultValue={sort ?? "newest"} aria-label="مرتب‌سازی">
        <option value="newest">جدیدترین</option>
        <option value="price_asc">ارزان‌ترین</option>
        <option value="price_desc">گران‌ترین</option>
        <option value="title">الفبایی</option>
      </select>
      <button>اعمال</button>
    </form>
  );
}
