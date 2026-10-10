import type { Metadata } from "next";
import { Suspense } from "react";
import CartView from "./CartView";

export const metadata: Metadata = { title: "سبد خرید", robots: { index: false, follow: false } };

export default function Page() {
  return (
    <Suspense fallback={<p className="muted">در حال بارگذاری...</p>}>
      <CartView />
    </Suspense>
  );
}
