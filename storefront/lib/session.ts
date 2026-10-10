"use client";
import { useEffect, useState } from "react";
import { api, ApiError, type Me } from "./client-api";

/** کاربر واردشده (از کوکی HttpOnly، با /auth/me). undefined = در حال بررسی، null = مهمان. */
export function useMe(): [Me | null | undefined, () => void] {
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    api<Me>("/auth/me")
      .then((m) => alive && setMe(m))
      .catch((e) => alive && setMe(e instanceof ApiError && e.status === 401 ? null : null));
    return () => {
      alive = false;
    };
  }, [tick]);
  return [me, () => setTick((t) => t + 1)];
}

/** آدرس بازگشت امن: فقط مسیرهای داخلی (جلوگیری از open redirect). */
export function safeNext(raw: string | null, fallback = "/account"): string {
  return raw && raw.startsWith("/") && !raw.startsWith("//") && !raw.startsWith("/\\") ? raw : fallback;
}
