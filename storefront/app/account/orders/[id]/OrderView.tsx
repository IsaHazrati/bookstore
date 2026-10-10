"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, ApiError, STATUS_LABEL, type Order, type PaymentInfo } from "@/lib/client-api";
import { faDateTime, toman } from "@/lib/format";

export default function OrderView() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [order, setOrder] = useState<Order | null>(null);
  const [info, setInfo] = useState<PaymentInfo | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [missing, setMissing] = useState(false);

  const load = useCallback(() => {
    api<Order>(`/orders/${encodeURIComponent(id)}`).then(setOrder).catch((e) => {
      if (e instanceof ApiError && e.status === 401) router.replace(`/login?next=/account/orders/${id}`);
      else if (e instanceof ApiError && (e.status === 404 || e.status === 422)) setMissing(true);
      else setError(e.message);
    });
  }, [id, router]);

  useEffect(() => {
    load();
    api<PaymentInfo>("/payment-info").then(setInfo).catch(() => {});
  }, [load]);

  async function act(fn: () => Promise<Order>, ok: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      setOrder(await fn());
      setNotice(ok);
    } catch (e) {
      setError(e instanceof Error ? e.message : "خطا");
    } finally {
      setBusy(false);
    }
  }

  function submitPayment(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const reference = String(new FormData(e.currentTarget).get("reference") ?? "").trim();
    void act(() => api<Order>(`/orders/${id}/payment`, { method: "POST", body: { reference } }),
      "شماره پیگیری ثبت شد. پس از بررسی، وضعیت سفارش به‌روز می‌شود.");
  }

  if (missing) return (<><h1>سفارش پیدا نشد</h1><p><Link href="/account">بازگشت به حساب من</Link></p></>);
  if (!order) return error ? <p className="error" role="alert">{error}</p> : <p className="muted">در حال بارگذاری...</p>;

  const canPay = order.status === "pending_payment" || order.status === "awaiting_confirmation";
  const hasDigital = order.items.some((i) => i.item_type === "digital");
  return (
    <>
      <p className="crumbs"><Link href="/account">حساب من</Link> / سفارش #{order.id.toLocaleString("fa-IR")}</p>
      <div className="row-between">
        <h1>سفارش #{order.id.toLocaleString("fa-IR")}</h1>
        <span className={`status s-${order.status}`}>{STATUS_LABEL[order.status]}</span>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}

      {canPay && (
        <section className="card pay">
          <h2>پرداخت</h2>
          <p>مبلغ <strong>{toman(order.total_price)}</strong> را به کارت زیر واریز کنید و شماره پیگیری را ثبت کنید:</p>
          {info?.card_number ? (
            <p className="card-number"><bdi dir="ltr">{info.card_number}</bdi>{info.card_holder && <span className="muted"> · به نام {info.card_holder}</span>}</p>
          ) : <p className="muted">شماره کارت فروشگاه هنوز تنظیم نشده است؛ با پشتیبانی تماس بگیرید.</p>}
          {order.status === "pending_payment" && order.expires_at && (
            <p className="muted">مهلت پرداخت: {faDateTime(order.expires_at)} — پس از آن سفارش خودکار لغو می‌شود.</p>
          )}
          {order.status === "awaiting_confirmation" && (
            <p className="notice">شماره پیگیری <bdi dir="ltr">{order.payment_reference}</bdi> ثبت شده و در انتظار بررسی است. اگر اشتباه وارد کرده‌اید، می‌توانید اصلاحش کنید.</p>
          )}
          <form className="row" onSubmit={submitPayment}>
            <input name="reference" required minLength={4} maxLength={120} placeholder="شماره پیگیری / شماره مرجع تراکنش" dir="ltr"
                   defaultValue={order.payment_reference ?? ""} aria-label="شماره پیگیری" />
            <button disabled={busy}>{order.status === "awaiting_confirmation" ? "اصلاح شماره پیگیری" : "ثبت پرداخت"}</button>
          </form>
          {order.status === "pending_payment" && (
            <button className="link-btn danger" disabled={busy}
                    onClick={() => confirm("این سفارش لغو شود؟") && act(() => api<Order>(`/orders/${id}/cancel`, { method: "POST" }), "سفارش لغو شد.")}>
              لغو سفارش
            </button>
          )}
        </section>
      )}

      {(order.status === "paid" || order.status === "completed") && hasDigital && (
        <p className="notice">کتاب‌های دیجیتال این سفارش در <Link href="/account">کتابخانه‌ی دیجیتال</Link> قابل دانلودند.</p>
      )}
      {order.status === "shipped" && (
        <p className="notice">بسته ارسال شد{order.tracking_code ? <> — کد رهگیری: <bdi dir="ltr">{order.tracking_code}</bdi></> : ""}.</p>
      )}
      {order.status === "cancelled" && order.cancel_reason && (
        <p className="muted">دلیل لغو: {order.cancel_reason === "payment deadline passed" ? "پایان مهلت پرداخت"
          : order.cancel_reason === "cancelled by customer" ? "لغو توسط شما" : order.cancel_reason}</p>
      )}

      <section className="card">
        <h2>اقلام</h2>
        <ul className="plain">
          {order.items.map((i) => (
            <li key={`${i.book_id}-${i.item_type}`} className="row-between">
              <span>{i.book_slug ? <Link href={`/books/${i.book_slug}`}>{i.title}</Link> : i.title}{" "}
                <span className="muted">({i.item_type === "digital" ? "دیجیتال" : `چاپی × ${i.quantity.toLocaleString("fa-IR")}`})</span></span>
              <span>{toman(Number(i.unit_price) * i.quantity)}</span>
            </li>
          ))}
        </ul>
        <p className="row-between"><span>جمع کتاب‌ها</span><span>{toman(order.subtotal)}</span></p>
        {Number(order.shipping_fee) > 0 && <p className="row-between"><span>هزینه‌ی ارسال</span><span>{toman(order.shipping_fee)}</span></p>}
        <p className="row-between total"><span>مبلغ کل</span><strong>{toman(order.total_price)}</strong></p>
      </section>

      {order.recipient_name && (
        <section className="card">
          <h2>ارسال به</h2>
          <p>{order.recipient_name} · <bdi dir="ltr">{order.phone}</bdi></p>
          <p className="muted">{order.province}، {order.city}، {order.shipping_address}{order.postal_code && <> · کد پستی <bdi dir="ltr">{order.postal_code}</bdi></>}</p>
        </section>
      )}
      <p className="muted">ثبت: {faDateTime(order.created_at)}{order.paid_at && ` · تأیید پرداخت: ${faDateTime(order.paid_at)}`}{order.shipped_at && ` · ارسال: ${faDateTime(order.shipped_at)}`}</p>
    </>
  );
}
