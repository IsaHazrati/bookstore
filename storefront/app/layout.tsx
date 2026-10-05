import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import { SITE_URL } from "@/lib/api";
import "./globals.css";

const NAME = "کتاب‌فروشی آنلاین";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: `${NAME} | خرید کتاب چاپی و دیجیتال`, template: `%s | ${NAME}` },
  description: "خرید آنلاین کتاب چاپی و نسخه‌ی دیجیتال (PDF و ایبوک) با بهترین قیمت.",
  openGraph: { type: "website", locale: "fa_IR", siteName: NAME },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fa" dir="rtl">
      <body>
        <header className="site-header">
          <div className="wrap">
            <Link href="/" className="logo">{NAME}</Link>
            <nav aria-label="منوی اصلی">
              <Link href="/books">همه‌ی کتاب‌ها</Link>
            </nav>
            <form action="/books" method="get" role="search">
              <input type="search" name="q" placeholder="جستجو..." maxLength={100} aria-label="جستجو" />
              <button>جستجو</button>
            </form>
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="site-footer">
          <div className="wrap">© {NAME}</div>
        </footer>
      </body>
    </html>
  );
}
