import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { Book, BookInput, BookType, Category } from "../types";

const TYPE_LABEL: Record<BookType, string> = { physical: "فقط فیزیکی", digital: "فقط دیجیتال", both: "فیزیکی و دیجیتال" };

const EMPTY: BookInput = {
  title: "", slug: null, author: "", publisher: null, isbn: null, description: "",
  published_date: null, book_type: "physical", price: 0, stock_quantity: 0, is_published: false, category_id: null,
};

// فیلد price در فرم به «تومان» است؛ API قیمت را به «ریال» می‌گیرد و برمی‌گرداند (×۱۰).
function toInput(b: Book): BookInput {
  return {
    title: b.title, slug: b.slug, author: b.author, publisher: b.publisher, isbn: b.isbn, description: b.description,
    published_date: b.published_date, book_type: b.book_type, price: Math.round(Number(b.price) / 10), stock_quantity: b.stock_quantity,
    is_published: b.is_published, category_id: b.category_id,
  };
}

export default function BookForm({ id, onClose }: { id: number | null; onClose: () => void }) {
  const [bookId, setBookId] = useState<number | null>(id);
  const [book, setBook] = useState<Book | null>(null);
  const [form, setForm] = useState<BookInput>(EMPTY);
  const [cats, setCats] = useState<Category[]>([]);
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.categories().then(setCats).catch(() => {});
  }, []);
  useEffect(() => {
    if (bookId === null) return;
    api.book(bookId).then((b) => { setBook(b); setForm(toInput(b)); }).catch((e) => setMsg({ kind: "error", text: e.message }));
  }, [bookId]);

  const set = <K extends keyof BookInput>(k: K, v: BookInput[K]) => setForm((f) => ({ ...f, [k]: v }));
  const hasDigital = form.book_type !== "physical";
  const hasPhysical = form.book_type !== "digital";

  async function guard(fn: () => Promise<void>, okText: string) {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
      setMsg({ kind: "ok", text: okText });
    } catch (e) {
      setMsg({ kind: "error", text: e instanceof Error ? e.message : "خطا" });
    } finally {
      setBusy(false);
    }
  }

  function save(e: FormEvent) {
    e.preventDefault();
    void guard(async () => {
      const payload: BookInput = { ...form, price: form.price * 10, slug: form.slug?.trim() || null, stock_quantity: hasPhysical ? form.stock_quantity : 0 };
      const saved = bookId === null ? await api.createBook(payload) : await api.updateBook(bookId, payload);
      setBook(saved);
      setForm(toInput(saved));
      setBookId(saved.id);
    }, "ذخیره شد");
  }

  function upload(kind: "cover" | "digital") {
    return (e: ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      e.target.value = "";
      if (!file || bookId === null) return;
      void guard(async () => {
        const saved = kind === "cover" ? await api.uploadCover(bookId, file) : await api.uploadDigital(bookId, file);
        setBook(saved);
      }, "فایل بارگذاری شد");
    };
  }

  return (
    <section>
      <button className="ghost" onClick={onClose}>← بازگشت به فهرست</button>
      <h2>{bookId === null ? "کتاب جدید" : `ویرایش: ${book?.title ?? ""}`}</h2>
      {msg && <p className={msg.kind === "ok" ? "notice" : "error"} role={msg.kind === "error" ? "alert" : "status"}>{msg.text}</p>}

      <form className="card grid" onSubmit={save}>
        <label>عنوان *<input required maxLength={255} value={form.title} onChange={(e) => set("title", e.target.value)} /></label>
        <label>نویسنده *<input required maxLength={160} value={form.author} onChange={(e) => set("author", e.target.value)} /></label>
        <label>ناشر<input maxLength={160} value={form.publisher ?? ""} onChange={(e) => set("publisher", e.target.value || null)} /></label>
        <label>شابک (ISBN)<input dir="ltr" maxLength={20} value={form.isbn ?? ""} onChange={(e) => set("isbn", e.target.value || null)} /></label>
        <label>تاریخ انتشار<input type="date" dir="ltr" value={form.published_date ?? ""} onChange={(e) => set("published_date", e.target.value || null)} /></label>
        <label>
          دسته‌بندی
          <select value={form.category_id ?? ""} onChange={(e) => set("category_id", e.target.value ? Number(e.target.value) : null)}>
            <option value="">— بدون دسته —</option>
            {cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
        <label>
          نوع کتاب
          <select value={form.book_type} onChange={(e) => set("book_type", e.target.value as BookType)}>
            {(Object.keys(TYPE_LABEL) as BookType[]).map((t) => <option key={t} value={t}>{TYPE_LABEL[t]}</option>)}
          </select>
        </label>
        <label>قیمت (تومان) *<input required type="number" min={0} step={1} dir="ltr" value={form.price} onChange={(e) => set("price", Math.max(0, Math.floor(Number(e.target.value) || 0)))} /></label>
        <label>
          موجودی انبار
          <input type="number" min={0} step={1} dir="ltr" disabled={!hasPhysical} value={hasPhysical ? form.stock_quantity : 0}
                 onChange={(e) => set("stock_quantity", Math.max(0, Math.floor(Number(e.target.value) || 0)))} />
        </label>
        <label>نشانی (slug) — خالی = خودکار<input dir="ltr" maxLength={280} value={form.slug ?? ""} onChange={(e) => set("slug", e.target.value || null)} /></label>
        <label className="wide">توضیحات<textarea rows={6} maxLength={20000} value={form.description} onChange={(e) => set("description", e.target.value)} /></label>
        <label className="check wide">
          <input type="checkbox" checked={form.is_published} onChange={(e) => set("is_published", e.target.checked)} />
          منتشر شود (در فروشگاه نمایش داده شود)
        </label>
        <div className="wide"><button disabled={busy}>{busy ? "..." : "ذخیره"}</button></div>
      </form>

      {bookId === null ? (
        <p className="muted">برای بارگذاری کاور و فایل دیجیتال، ابتدا کتاب را ذخیره کنید.</p>
      ) : (
        <div className="card grid">
          <div>
            <h3>تصویر جلد</h3>
            {book?.cover_image_url && <img className="cover" src={book.cover_image_url} alt="جلد کتاب" />}
            <input type="file" accept=".jpg,.jpeg,.png,.webp" onChange={upload("cover")} disabled={busy} />
            <p className="muted">JPG / PNG / WebP، حداکثر ۵ مگابایت</p>
          </div>
          {hasDigital && (
            <div>
              <h3>فایل دیجیتال</h3>
              <p>{book?.has_digital_file ? "✅ فایل بارگذاری شده است" : "⚠️ هنوز فایلی بارگذاری نشده (بدون فایل نمی‌توان منتشر کرد)"}</p>
              <input type="file" accept=".pdf,.epub" onChange={upload("digital")} disabled={busy} />
              {book?.has_digital_file && (
                <button className="danger" type="button" disabled={busy}
                        onClick={() => void guard(async () => setBook(await api.removeDigital(bookId)), "فایل حذف شد")}>
                  حذف فایل
                </button>
              )}
              <p className="muted">PDF / EPUB، حداکثر ۱۰۰ مگابایت. این فایل عمومی نیست و فقط پس از خرید قابل دانلود خواهد بود.</p>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
