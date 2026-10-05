import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Category } from "../types";

export default function Categories() {
  const [items, setItems] = useState<Category[]>([]);
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<{ id: number; name: string } | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => api.categories().then(setItems).catch((e) => setError(e.message)), []);
  useEffect(() => void load(), [load]);

  async function run(fn: () => Promise<unknown>) {
    setError("");
    try {
      await fn();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "خطا");
    }
  }

  function add(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    void run(async () => {
      await api.createCategory(name.trim());
      setName("");
    });
  }

  return (
    <section>
      <h2>دسته‌بندی‌ها</h2>
      {error && <p className="error" role="alert">{error}</p>}
      <form className="row" onSubmit={add}>
        <input placeholder="نام دسته‌بندی جدید" value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
        <button>افزودن</button>
      </form>
      <table>
        <thead>
          <tr><th>نام</th><th>نشانی (slug)</th><th /></tr>
        </thead>
        <tbody>
          {items.map((c) => (
            <tr key={c.id}>
              <td>
                {editing?.id === c.id ? (
                  <input value={editing.name} onChange={(e) => setEditing({ id: c.id, name: e.target.value })} maxLength={120} />
                ) : (
                  c.name
                )}
              </td>
              <td dir="ltr">{c.slug}</td>
              <td className="actions">
                {editing?.id === c.id ? (
                  <>
                    <button onClick={() => run(async () => { await api.updateCategory(c.id, editing.name.trim()); setEditing(null); })}>ذخیره</button>
                    <button className="ghost" onClick={() => setEditing(null)}>انصراف</button>
                  </>
                ) : (
                  <>
                    <button className="ghost" onClick={() => setEditing({ id: c.id, name: c.name })}>ویرایش</button>
                    <button className="danger" onClick={() => confirm(`حذف «${c.name}»؟`) && run(() => api.deleteCategory(c.id))}>حذف</button>
                  </>
                )}
              </td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={3} className="muted">دسته‌بندی‌ای ثبت نشده است.</td></tr>}
        </tbody>
      </table>
    </section>
  );
}
