"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { api } from "@/lib/client-api";
import { safeNext } from "@/lib/session";

export default function RegisterView() {
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const email = String(f.get("email")).trim();
    const password = String(f.get("password"));
    if (password !== String(f.get("password2"))) {
      setError("رمز عبور و تکرار آن یکسان نیستند.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api("/auth/register", { method: "POST", body: { email, password, full_name: String(f.get("full_name")).trim() } });
      await api("/auth/login", { method: "POST", body: { email, password } });
      router.replace(next);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطا");
      setBusy(false);
    }
  }

  return (
    <form className="card auth-form" onSubmit={submit}>
      <h1>ثبت‌نام</h1>
      {error && <p className="error" role="alert">{error}</p>}
      <label>نام و نام خانوادگی<input name="full_name" maxLength={120} autoComplete="name" /></label>
      <label>ایمیل<input name="email" type="email" required autoComplete="email" dir="ltr" /></label>
      <label>رمز عبور (حداقل ۸ کاراکتر)<input name="password" type="password" required minLength={8} maxLength={128} autoComplete="new-password" dir="ltr" /></label>
      <label>تکرار رمز عبور<input name="password2" type="password" required minLength={8} maxLength={128} autoComplete="new-password" dir="ltr" /></label>
      <button disabled={busy}>{busy ? "در حال ثبت‌نام..." : "ثبت‌نام"}</button>
      <p className="muted">قبلاً ثبت‌نام کرده‌اید؟ <Link href={`/login?next=${encodeURIComponent(next)}`}>وارد شوید</Link></p>
    </form>
  );
}
