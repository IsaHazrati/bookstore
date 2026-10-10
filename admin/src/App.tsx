import { useEffect, useState } from "react";
import { api, fetchMe, hasToken, logout, setUnauthorizedHandler } from "./api";
import Books from "./pages/Books";
import Categories from "./pages/Categories";
import Login from "./pages/Login";
import Orders from "./pages/Orders";
import type { Me } from "./types";

type Tab = "orders" | "books" | "categories";

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [checking, setChecking] = useState(hasToken());
  const [notice, setNotice] = useState("");
  const [tab, setTab] = useState<Tab>("orders");
  const [pending, setPending] = useState(0);
  const refreshPending = () => { api.orderSummary().then((s) => setPending(s.awaiting_confirmation + s.to_ship)).catch(() => {}); };

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setMe(null);
      setNotice("نشست شما منقضی شد. دوباره وارد شوید.");
    });
    if (!hasToken()) return;
    fetchMe()
      .then((m) => setMe(m.role === "admin" ? m : null))
      .catch(() => setMe(null))
      .finally(() => setChecking(false));
  }, []);

  useEffect(() => { if (me) refreshPending(); }, [me]);

  if (checking) return <p className="center">در حال بارگذاری...</p>;
  if (!me) {
    return (
      <Login
        notice={notice}
        onDone={() => fetchMe().then((m) => { setNotice(""); setMe(m); })}
      />
    );
  }

  return (
    <div className="shell">
      <header>
        <strong>پنل مدیریت کتاب‌فروشی</strong>
        <nav>
          <button className={tab === "orders" ? "active" : "ghost"} onClick={() => { setTab("orders"); refreshPending(); }}>
            سفارش‌ها{pending > 0 && <span className="badge" title="در انتظار تأیید یا ارسال">{pending.toLocaleString("fa-IR")}</span>}
          </button>
          <button className={tab === "books" ? "active" : "ghost"} onClick={() => setTab("books")}>کتاب‌ها</button>
          <button className={tab === "categories" ? "active" : "ghost"} onClick={() => setTab("categories")}>دسته‌بندی‌ها</button>
        </nav>
        <span className="muted" dir="ltr">{me.email}</span>
        <button className="ghost" onClick={() => { logout(); setMe(null); }}>خروج</button>
      </header>
      <main>{tab === "orders" ? <Orders onChange={refreshPending} /> : tab === "books" ? <Books /> : <Categories />}</main>
    </div>
  );
}
