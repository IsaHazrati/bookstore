import type { Metadata } from "next";
import { Suspense } from "react";
import CheckoutView from "./CheckoutView";

export const metadata: Metadata = { title: "تکمیل خرید", robots: { index: false, follow: false } };

export default function Page() {
  return (
    <Suspense fallback={<p className="muted">در حال بارگذاری...</p>}>
      <CheckoutView />
    </Suspense>
  );
}
