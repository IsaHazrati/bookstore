import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { BookPage } from "../types";
import BookForm from "./BookForm";

const TYPE_LABEL = { physical: "فیزیکی", digital: "دیجیتال", both: "هر دو" } as const;

export default function Books() {
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [data, setData] = useState<BookPage | null>(null);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.books(page, query).then(setData).catch((e) => setError(e.message));
  }, [page, query]);
  useEffect(() => { if (editing === null) load(); }, [load, editing]);

  if (editing !== null) return <BookForm id={editing === "new" ? null : editing} onClose={() => setEditing(null)} />;

  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  async function remove(id: number, title: string) {
    if (!confirm(`حذف «${title}»؟ این کار قابل بازگشت نیست.`)) return;
    try {
      await api.deleteBook(id);
      setError("");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "خطا");
    }
  }

  return (
    <section>
      <h2>کتاب‌ها</h2>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="row">
        <form className="row" onSubmit={(e) => { e.preventDefault(); setPage(1); setQuery(q.trim()); }}>
          <input placeholder="جستجوی عنوان یا نویسنده" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="ghost">جستجو</button>
        </form>
        <button onClick={() => setEditing("new")}>+ کتاب جدید</button>
      </div>
      <table>
        <thead>
          <tr><th>عنوان</th><th>نویسنده</th><th>نوع</th><th>قیمت</th><th>موجودی</th><th>وضعیت</th><th /></tr>
        </thead>
        <tbody>
          {data?.items.map((b) => (
            <tr key={b.id}>
              <td>{b.title}</td>
              <td>{b.author}</td>
              <td>{TYPE_LABEL[b.book_type]}</td>
              <td dir="ltr">{Number(b.price).toLocaleString("fa-IR")}</td>
              <td>{b.book_type === "digital" ? "—" : b.stock_quantity.toLocaleString("fa-IR")}</td>
              <td>{b.is_published ? "منتشر شده" : "پیش‌نویس"}</td>
              <td className="actions">
                <button className="ghost" onClick={() => setEditing(b.id)}>ویرایش</button>
                <button className="danger" onClick={() => remove(b.id, b.title)}>حذف</button>
              </td>
            </tr>
          ))}
          {data && data.items.length === 0 && <tr><td colSpan={7} className="muted">کتابی پیدا نشد.</td></tr>}
        </tbody>
      </table>
      {data && data.total > data.page_size && (
        <div className="row pager">
          <button className="ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>قبلی</button>
          <span>صفحه {page.toLocaleString("fa-IR")} از {pages.toLocaleString("fa-IR")}</span>
          <button className="ghost" disabled={page >= pages} onClick={() => setPage(page + 1)}>بعدی</button>
        </div>
      )}
    </section>
  );
}
