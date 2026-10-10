import type { Metadata } from "next";
import { Suspense } from "react";
import RegisterView from "./RegisterView";

export const metadata: Metadata = { title: "ثبت‌نام", robots: { index: false, follow: false } };

export default function Page() {
  return (
    <Suspense fallback={<p className="muted">در حال بارگذاری...</p>}>
      <RegisterView />
    </Suspense>
  );
}
