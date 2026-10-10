"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, STATUS_LABEL, type LibraryItem, type Order } from "@/lib/client-api";
import { faDateTime, toman } from "@/lib/format";
import { useMe } from "@/lib/session";

export default function AccountView() {
  const router = useRouter();
  const [me] = useMe();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [library, setLibrary] = useState<LibraryItem[] | null>(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    if (me === null) router.replace("/login?next=/account");
    if (!me) return;
    api<{ items: Order[] }>("/orders?page_size=50").then((d) => setOrders(d.items)).catch((e) => setError(e.message));
    api<LibraryItem[]>("/me/library").then(setLibrary).catch((e) => setError(e.message));
  }, [me, router]);

  async function download(item: LibraryItem) {
    setBusyId(item.access_id);
    setError("");
    try {
      const link = await api<{ url: string; downloads_left: number }>(`/me/library/${item.access_id}/link`, { method: "POST" });
      setLibrary((lib) => lib?.map((x) => (x.access_id === item.access_id ? { ...x, downloads_left: link.downloads_left } : x)) ?? null);
      window.location.assign(link.url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "خطا");
    } finally {
      setBusyId(null);
    }
  }

  async function logout() {
    await api("/auth/logout", { method: "POST" }).catch(() => {});
    router.replace("/");
    router.refresh();
  }

  if (!me) return <p className="muted">در حال بارگذاری...</p>;
  return (
    <>
      <div className="row-between">
        <h1>حساب من</h1>
        <span className="muted"><bdi dir="ltr">{me.email}</bdi> · <button className="link-btn" onClick={logout}>خروج</button></span>
      </div>
      {error && <p className="error" role="alert">{error}</p>}

      <h2>کتابخانه‌ی دیجیتال</h2>
      {library === null ? <p className="muted">در حال بارگذاری...</p> : library.length === 0 ? (
        <p className="muted">هنوز کتاب دیجیتالی ندارید. کتاب‌های دیجیتال بعد از تأیید پرداخت اینجا قابل دانلودند.</p>
      ) : (
        <ul className="plain library">
          {library.map((b) => (
            <li key={b.access_id} className="card row-between">
              <span><Link href={`/books/${b.slug}`}><strong>{b.title}</strong></Link> <span className="muted">· {b.author} · {b.file_format}</span></span>
              <span className="row-between">
                <span className="muted">{b.downloads_left.toLocaleString("fa-IR")} دانلود باقی‌مانده</span>
                <button onClick={() => download(b)} disabled={busyId === b.access_id || b.downloads_left === 0}>
                  {busyId === b.access_id ? "..." : "دانلود"}
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      <h2>سفارش‌ها</h2>
      {orders === null ? <p className="muted">در حال بارگذاری...</p> : orders.length === 0 ? (
        <p className="muted">هنوز سفارشی ثبت نکرده‌اید. <Link href="/books">مشاهده‌ی کتاب‌ها ←</Link></p>
      ) : (
        <table className="orders">
          <thead><tr><th>شماره</th><th>تاریخ</th><th>مبلغ</th><th>وضعیت</th><th /></tr></thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id}>
                <td>#{o.id.toLocaleString("fa-IR")}</td>
                <td>{faDateTime(o.created_at)}</td>
                <td>{toman(o.total_price)}</td>
                <td><span className={`status s-${o.status}`}>{STATUS_LABEL[o.status]}</span></td>
                <td><Link href={`/account/orders/${o.id}`}>{o.status === "pending_payment" ? "پرداخت ←" : "جزئیات ←"}</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
