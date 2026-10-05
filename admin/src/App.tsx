import { useEffect, useState } from "react";
import { fetchMe, hasToken, logout, setUnauthorizedHandler } from "./api";
import Books from "./pages/Books";
import Categories from "./pages/Categories";
import Login from "./pages/Login";
import type { Me } from "./types";

type Tab = "books" | "categories";

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [checking, setChecking] = useState(hasToken());
  const [notice, setNotice] = useState("");
  const [tab, setTab] = useState<Tab>("books");

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
          <button className={tab === "books" ? "active" : "ghost"} onClick={() => setTab("books")}>کتاب‌ها</button>
          <button className={tab === "categories" ? "active" : "ghost"} onClick={() => setTab("categories")}>دسته‌بندی‌ها</button>
        </nav>
        <span className="muted" dir="ltr">{me.email}</span>
        <button className="ghost" onClick={() => { logout(); setMe(null); }}>خروج</button>
      </header>
      <main>{tab === "books" ? <Books /> : <Categories />}</main>
    </div>
  );
}
