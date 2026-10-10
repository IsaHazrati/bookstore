"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { api } from "@/lib/client-api";
import { safeNext } from "@/lib/session";

export default function LoginView() {
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api("/auth/login", { method: "POST", body: { email: String(f.get("email")).trim(), password: String(f.get("password")) } });
      router.replace(next);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطا");
      setBusy(false);
    }
  }

  return (
    <form className="card auth-form" onSubmit={submit}>
      <h1>ورود</h1>
      {error && <p className="error" role="alert">{error}</p>}
      <label>ایمیل<input name="email" type="email" required autoComplete="username" dir="ltr" /></label>
      <label>رمز عبور<input name="password" type="password" required autoComplete="current-password" dir="ltr" /></label>
      <button disabled={busy}>{busy ? "در حال ورود..." : "ورود"}</button>
      <p className="muted">حساب ندارید؟ <Link href={`/register?next=${encodeURIComponent(next)}`}>ثبت‌نام کنید</Link></p>
    </form>
  );
}
