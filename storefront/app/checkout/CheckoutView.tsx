"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { api, type Order, type PaymentInfo } from "@/lib/client-api";
import { cartSubtotal, clearCart, useCart } from "@/lib/cart";
import { toman } from "@/lib/format";
import { useMe } from "@/lib/session";

export default function CheckoutView() {
  const router = useRouter();
  const items = useCart();
  const [me] = useMe();
  const [info, setInfo] = useState<PaymentInfo | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<PaymentInfo>("/payment-info").then(setInfo).catch(() => {});
  }, []);
  useEffect(() => {
    if (me === null) router.replace("/login?next=/checkout");
  }, [me, router]);

  if (me === undefined) return <p className="muted">در حال بارگذاری...</p>;
  if (me === null) return null;
  if (items.length === 0) {
    return (<><h1>تکمیل خرید</h1><p className="muted">سبد خرید خالی است.</p><p><Link href="/books">مشاهده‌ی کتاب‌ها ←</Link></p></>);
  }

  const hasPhysical = items.some((i) => i.item_type === "physical");
  const subtotal = cartSubtotal(items);
  const shipping = hasPhysical ? info?.shipping_fee ?? 0 : 0;

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const v = (k: string) => String(f.get(k) ?? "").trim();
    setBusy(true);
    setError("");
    try {
      const order = await api<Order>("/orders", {
        method: "POST",
        body: {
          items: items.map((i) => ({ book_id: i.book_id, item_type: i.item_type, quantity: i.quantity })),
          shipping: hasPhysical
            ? { recipient_name: v("recipient_name"), phone: v("phone"), province: v("province"), city: v("city"), address: v("address") }
            : null,
          customer_note: v("customer_note") || null,
        },
      });
      clearCart();
      router.replace(`/account/orders/${order.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطا");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="checkout">
      <h1>تکمیل خرید</h1>
      {error && <p className="error" role="alert">{error}</p>}
      {hasPhysical ? (
        <fieldset className="card grid-form">
          <legend>اطلاعات گیرنده</legend>
          <label>نام و نام خانوادگی گیرنده<input name="recipient_name" required minLength={2} maxLength={120} defaultValue={me.full_name} autoComplete="name" /></label>
          <label>موبایل<input name="phone" required inputMode="tel" placeholder="۰۹۱۲۱۲۳۴۵۶۷" maxLength={20} autoComplete="tel" dir="ltr" /></label>
          <label>استان<input name="province" required minLength={2} maxLength={60} /></label>
          <label>شهر<input name="city" required minLength={2} maxLength={60} /></label>
          <label className="wide">آدرس کامل<textarea name="address" required minLength={5} maxLength={500} rows={3} autoComplete="street-address" /></label>
          <p className="muted wide">کد پستی را هنگام ارسال بسته از شما می‌پرسیم.</p>
        </fieldset>
      ) : (
        <p className="muted">سفارش شما فقط کتاب دیجیتال دارد؛ نیازی به آدرس نیست. پس از تأیید پرداخت، کتاب در «حساب من» قابل دانلود است.</p>
      )}
      <label className="card">یادداشت برای فروشگاه (اختیاری)<textarea name="customer_note" maxLength={500} rows={2} /></label>

      <div className="card summary">
        <h2>خلاصه‌ی سفارش</h2>
        <ul className="plain">
          {items.map((i) => (
            <li key={`${i.book_id}-${i.item_type}`} className="row-between">
              <span>{i.title} <span className="muted">({i.item_type === "digital" ? "دیجیتال" : `چاپی × ${i.quantity.toLocaleString("fa-IR")}`})</span></span>
              <span>{toman(Number(i.price) * i.quantity)}</span>
            </li>
          ))}
        </ul>
        <p className="row-between"><span>جمع کتاب‌ها</span><span>{toman(subtotal)}</span></p>
        {hasPhysical && <p className="row-between"><span>هزینه‌ی ارسال</span><span>{shipping ? toman(shipping) : "رایگان"}</span></p>}
        <p className="row-between total"><span>مبلغ قابل پرداخت</span><strong>{toman(subtotal + shipping)}</strong></p>
        <p className="muted">
          پرداخت به‌صورت کارت‌به‌کارت است. بعد از ثبت سفارش، شماره کارت فروشگاه نمایش داده می‌شود و
          {info ? ` ${info.payment_hours.toLocaleString("fa-IR")} ساعت ` : " "}
          فرصت دارید پرداخت کنید و شماره پیگیری را ثبت کنید.
        </p>
        <button disabled={busy}>{busy ? "در حال ثبت..." : "ثبت سفارش"}</button>
      </div>
    </form>
  );
}
