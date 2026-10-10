import type { Metadata } from "next";
import { Suspense } from "react";
import AccountView from "./AccountView";

export const metadata: Metadata = { title: "حساب من", robots: { index: false, follow: false } };

export default function Page() {
  return (
    <Suspense fallback={<p className="muted">در حال بارگذاری...</p>}>
      <AccountView />
    </Suspense>
  );
}
