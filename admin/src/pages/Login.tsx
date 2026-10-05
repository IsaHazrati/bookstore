import { FormEvent, useState } from "react";
import { login } from "../api";

export default function Login({ onDone, notice }: { onDone: () => void; notice?: string }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email.trim(), password);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطا");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card login" onSubmit={submit}>
      <h1>ورود به پنل مدیریت</h1>
      {notice && <p className="notice">{notice}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <label>
        ایمیل
        <input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} dir="ltr" />
      </label>
      <label>
        رمز عبور
        <input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} dir="ltr" />
      </label>
      <button disabled={busy}>{busy ? "در حال ورود..." : "ورود"}</button>
    </form>
  );
}
