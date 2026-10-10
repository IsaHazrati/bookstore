import type { Metadata } from "next";
import { Suspense } from "react";
import LoginView from "./LoginView";

export const metadata: Metadata = { title: "ورود", robots: { index: false, follow: false } };

export default function Page() {
  return (
    <Suspense fallback={<p className="muted">در حال بارگذاری...</p>}>
      <LoginView />
    </Suspense>
  );
}
