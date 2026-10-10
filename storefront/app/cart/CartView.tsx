"use client";
import Link from "next/link";
import { cartSubtotal, removeFromCart, setQuantity, useCart } from "@/lib/cart";
import { toman } from "@/lib/format";

export default function CartView() {
  const items = useCart();
  if (items.length === 0) {
    return (
      <>
        <h1>سبد خرید</h1>
        <p className="muted">سبد خرید شما خالی است.</p>
        <p><Link href="/books">مشاهده‌ی کتاب‌ها ←</Link></p>
      </>
    );
  }
  const hasPhysical = items.some((i) => i.item_type === "physical");
  return (
    <>
      <h1>سبد خرید</h1>
      <ul className="cart-list">
        {items.map((i) => (
          <li key={`${i.book_id}-${i.item_type}`} className="card cart-row">
            <div>
              <Link href={`/books/${i.slug}`}><strong>{i.title}</strong></Link>
              <p className="muted">{i.item_type === "digital" ? "نسخه‌ی دیجیتال" : "نسخه‌ی چاپی"} · {toman(i.price)}</p>
            </div>
            <div className="cart-actions">
              {i.item_type === "physical" ? (
                <label className="qty">
                  تعداد
                  <select value={i.quantity} onChange={(e) => setQuantity(i.book_id, i.item_type, Number(e.target.value))}>
                    {Array.from({ length: 10 }, (_, n) => n + 1).map((n) => <option key={n} value={n}>{n.toLocaleString("fa-IR")}</option>)}
                  </select>
                </label>
              ) : <span className="muted">۱ نسخه</span>}
              <strong>{toman(Number(i.price) * i.quantity)}</strong>
              <button className="link-btn" onClick={() => removeFromCart(i.book_id, i.item_type)} aria-label={`حذف ${i.title}`}>حذف</button>
            </div>
          </li>
        ))}
      </ul>
      <div className="card summary">
        <p className="row-between"><span>جمع کتاب‌ها</span><strong>{toman(cartSubtotal(items))}</strong></p>
        {hasPhysical && <p className="muted">هزینه‌ی ارسال در مرحله‌ی بعد اضافه می‌شود.</p>}
        <p className="muted">قیمت و موجودی نهایی هنگام ثبت سفارش بررسی می‌شود.</p>
        <Link href="/checkout" className="btn">ادامه‌ی خرید</Link>
      </div>
    </>
  );
}
