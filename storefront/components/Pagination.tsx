import Link from "next/link";

/** لینک‌های معمولی (بدون JS) تا موتورهای جستجو صفحات بعد را دنبال کنند. */
export default function Pagination({
  page, pages, hrefFor,
}: { page: number; pages: number; hrefFor: (page: number) => string }) {
  if (pages <= 1) return null;
  return (
    <nav className="pager" aria-label="صفحه‌بندی">
      {page > 1 ? <Link href={hrefFor(page - 1)} rel="prev">قبلی</Link> : <span className="disabled">قبلی</span>}
      <span>صفحه {page.toLocaleString("fa-IR")} از {pages.toLocaleString("fa-IR")}</span>
      {page < pages ? <Link href={hrefFor(page + 1)} rel="next">بعدی</Link> : <span className="disabled">بعدی</span>}
    </nav>
  );
}
