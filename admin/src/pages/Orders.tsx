import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Order, OrderPage, OrderStatus } from "../types";

export const STATUS_LABEL: Record<OrderStatus, string> = {
  pending_payment: "در انتظار پرداخت",
  awaiting_confirmation: "در انتظار تأیید پرداخت",
  paid: "پرداخت‌شده (آماده‌ی ارسال)",
  shipped: "ارسال‌شده",
  completed: "تکمیل‌شده",
  cancelled: "لغوشده",
};

const toman = (rial: string | number) => `${Math.round(Number(rial) / 10).toLocaleString("fa-IR")} تومان`;
const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString("fa-IR", { dateStyle: "short", timeStyle: "short" }) : "—");

export default function Orders({ onChange }: { onChange: () => void }) {
  const [openId, setOpenId] = useState<number | null>(null);
  const [status, setStatus] = useState<OrderStatus | "">("awaiting_confirmation");
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<OrderPage | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.orders(page, status, query).then(setData).catch((e) => setError(e.message));
  }, [page, status, query]);
  useEffect(() => { if (openId === null) load(); }, [load, openId]);

  if (openId !== null) return <OrderDetail id={openId} onClose={() => { setOpenId(null); onChange(); }} />;
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <section>
      <h2>سفارش‌ها</h2>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="row">
        <select value={status} onChange={(e) => { setPage(1); setStatus(e.target.value as OrderStatus | ""); }} aria-label="وضعیت">
          <option value="">همه‌ی وضعیت‌ها</option>
          {(Object.keys(STATUS_LABEL) as OrderStatus[]).map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
        </select>
        <form className="row" onSubmit={(e) => { e.preventDefault(); setPage(1); setQuery(q.trim()); }}>
          <input placeholder="شماره سفارش، ایمیل، موبایل یا نام گیرنده" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="ghost">جستجو</button>
        </form>
      </div>
      <table>
        <thead><tr><th>#</th><th>تاریخ</th><th>مشتری</th><th>اقلام</th><th>مبلغ</th><th>وضعیت</th><th /></tr></thead>
        <tbody>
          {data?.items.map((o) => (
            <tr key={o.id}>
              <td>{o.id.toLocaleString("fa-IR")}</td>
              <td>{when(o.created_at)}</td>
              <td dir="ltr" style={{ textAlign: "end" }}>{o.user_email}</td>
              <td>{o.items.map((i) => `${i.title}${i.item_type === "digital" ? " (دیجیتال)" : ` ×${i.quantity.toLocaleString("fa-IR")}`}`).join("، ")}</td>
              <td>{toman(o.total_price)}</td>
              <td><span className={`status s-${o.status}`}>{STATUS_LABEL[o.status]}</span></td>
              <td className="actions"><button className="ghost" onClick={() => setOpenId(o.id)}>بررسی</button></td>
            </tr>
          ))}
          {data && data.items.length === 0 && <tr><td colSpan={7} className="muted">سفارشی با این شرایط نیست.</td></tr>}
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

function OrderDetail({ id, onClose }: { id: number; onClose: () => void }) {
  const [order, setOrder] = useState<Order | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [postal, setPostal] = useState("");
  const [note, setNote] = useState("");
  const [tracking, setTracking] = useState("");

  const fill = (o: Order) => { setOrder(o); setPostal(o.postal_code ?? ""); setNote(o.admin_note ?? ""); setTracking(o.tracking_code ?? ""); };
  useEffect(() => { api.order(id).then(fill).catch((e) => setMsg({ kind: "error", text: e.message })); }, [id]);

  async function run(fn: () => Promise<Order>, ok: string) {
    setBusy(true);
    setMsg(null);
    try {
      fill(await fn());
      setMsg({ kind: "ok", text: ok });
    } catch (e) {
      setMsg({ kind: "error", text: e instanceof Error ? e.message : "خطا" });
    } finally {
      setBusy(false);
    }
  }
  const ask = (text: string) => {
    const r = prompt(text);
    return r && r.trim().length >= 2 ? r.trim() : null;
  };

  if (!order) return <section><button className="ghost" onClick={onClose}>← بازگشت</button>{msg && <p className="error">{msg.text}</p>}</section>;
  const s = order.status;
  const physical = order.items.some((i) => i.item_type === "physical");

  return (
    <section>
      <button className="ghost" onClick={onClose}>← بازگشت به فهرست</button>
      <h2>سفارش #{order.id.toLocaleString("fa-IR")} <span className={`status s-${s}`}>{STATUS_LABEL[s]}</span></h2>
      {msg && <p className={msg.kind === "ok" ? "notice" : "error"} role={msg.kind === "error" ? "alert" : "status"}>{msg.text}</p>}

      <div className="card grid">
        <div>
          <h3>پرداخت</h3>
          <p>مبلغ: <strong>{toman(order.total_price)}</strong>{Number(order.shipping_fee) > 0 && <span className="muted"> (شامل ارسال {toman(order.shipping_fee)})</span>}</p>
          <p>شماره پیگیری مشتری: {order.payment_reference ? <strong dir="ltr">{order.payment_reference}</strong> : <span className="muted">هنوز ثبت نشده</span>}</p>
          <p className="muted">ثبت سفارش: {when(order.created_at)} · ثبت پرداخت: {when(order.payment_submitted_at)} · تأیید: {when(order.paid_at)}</p>
          {s === "pending_payment" && <p className="muted">مهلت پرداخت: {when(order.expires_at)}</p>}
          <div className="row">
            {(s === "awaiting_confirmation" || s === "pending_payment") && (
              <button disabled={busy} onClick={() => confirm(`واریز ${toman(order.total_price)} را تأیید می‌کنید؟`) && run(() => api.confirmPayment(id), "پرداخت تأیید شد.")}>
                تأیید پرداخت
              </button>
            )}
            {s === "awaiting_confirmation" && (
              <button className="ghost" disabled={busy} onClick={() => { const r = ask("دلیل رد پرداخت (به مشتری فرصت دوباره داده می‌شود):"); if (r) void run(() => api.rejectPayment(id, r), "پرداخت رد شد؛ سفارش به انتظار پرداخت برگشت."); }}>
                رد پرداخت
              </button>
            )}
          </div>
        </div>
        <div>
          <h3>مشتری و ارسال</h3>
          <p dir="ltr" style={{ textAlign: "end" }}>{order.user_email}</p>
          {physical ? (
            <>
              <p>{order.recipient_name} · <span dir="ltr">{order.phone}</span></p>
              <p className="muted">{order.province}، {order.city}، {order.shipping_address}</p>
            </>
          ) : <p className="muted">فقط دیجیتال؛ ارسال ندارد.</p>}
          {order.customer_note && <p>یادداشت مشتری: {order.customer_note}</p>}
        </div>
      </div>

      <div className="card">
        <h3>اقلام</h3>
        <table>
          <thead><tr><th>کتاب</th><th>نوع</th><th>تعداد</th><th>قیمت واحد</th></tr></thead>
          <tbody>
            {order.items.map((i) => (
              <tr key={`${i.book_id}-${i.item_type}`}>
                <td>{i.title}</td><td>{i.item_type === "digital" ? "دیجیتال" : "چاپی"}</td>
                <td>{i.quantity.toLocaleString("fa-IR")}</td><td>{toman(i.unit_price)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <form className="card grid" onSubmit={(e: FormEvent) => { e.preventDefault(); void run(() => api.patchOrder(id, { postal_code: postal || null, admin_note: note || null }), "ذخیره شد."); }}>
        <label>کد پستی (۱۰ رقم)<input dir="ltr" value={postal} maxLength={20} onChange={(e) => setPostal(e.target.value)} placeholder="هنگام ارسال از مشتری بگیرید" /></label>
        <label className="wide">یادداشت داخلی (مشتری نمی‌بیند)<textarea rows={3} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} /></label>
        <div className="wide"><button disabled={busy} className="ghost">ذخیره‌ی کد پستی و یادداشت</button></div>
      </form>

      {(s === "paid" || s === "shipped") && physical && (
        <div className="card row">
          {s === "paid" && (
            <>
              <input dir="ltr" placeholder="کد رهگیری پست (اختیاری)" value={tracking} maxLength={60} onChange={(e) => setTracking(e.target.value)} />
              <button disabled={busy} onClick={() => run(() => api.shipOrder(id, tracking.trim()), "سفارش ارسال‌شده ثبت شد.")}>ثبت ارسال</button>
            </>
          )}
          {s === "shipped" && (
            <>
              <span>کد رهگیری: <strong dir="ltr">{order.tracking_code ?? "—"}</strong></span>
              <button disabled={busy} onClick={() => run(() => api.completeOrder(id), "سفارش تکمیل شد.")}>تحویل شد / تکمیل</button>
            </>
          )}
        </div>
      )}

      {(s === "pending_payment" || s === "awaiting_confirmation" || s === "paid") && (
        <p>
          <button className="danger" disabled={busy} onClick={() => { const r = ask("دلیل لغو (موجودی برمی‌گردد و دسترسی دیجیتال این سفارش حذف می‌شود):"); if (r) void run(() => api.cancelOrder(id, r), "سفارش لغو شد."); }}>
            لغو سفارش
          </button>
        </p>
      )}
      {s === "cancelled" && <p className="muted">لغو در {when(order.cancelled_at)}: {order.cancel_reason}</p>}
    </section>
  );
}
