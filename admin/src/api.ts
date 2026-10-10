import type { Book, BookInput, BookPage, Category, Me, Order, OrderPage, OrderStatus } from "./types";

const TOKEN_KEY = "admin_token";
let token: string | null = null;
try {
  token = sessionStorage.getItem(TOKEN_KEY);
} catch {
  /* sessionStorage ممکن است در دسترس نباشد */
}

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

export function hasToken(): boolean {
  return token !== null;
}

function saveToken(t: string | null) {
  token = t;
  try {
    if (t) sessionStorage.setItem(TOKEN_KEY, t);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function describe(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg ?? ""}`)
      .join(" | ");
  }
  return "خطای ناشناخته";
}

async function request<T>(method: string, path: string, body?: unknown, form?: FormData): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let res: Response;
  try {
    res = await fetch(path, {
      method,
      headers,
      body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
    });
  } catch {
    throw new ApiError(0, "ارتباط با سرور برقرار نشد");
  }
  if (res.status === 204) return undefined as T;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    // در صفحه‌ی ورود ۴۰۱ یعنی رمز اشتباه، نه انقضای نشست
    if (res.status === 401 && token && !path.endsWith("/auth/login")) {
      saveToken(null);
      onUnauthorized();
    }
    throw new ApiError(res.status, describe(data.detail));
  }
  return data as T;
}

export async function login(email: string, password: string): Promise<Me> {
  const t = await request<{ access_token: string }>("POST", "/api/v1/auth/login", { email, password });
  saveToken(t.access_token);
  const me = await request<Me>("GET", "/api/v1/auth/me");
  if (me.role !== "admin") {
    saveToken(null);
    throw new ApiError(403, "این حساب دسترسی مدیر ندارد");
  }
  return me;
}

export const logout = () => saveToken(null);
export const fetchMe = () => request<Me>("GET", "/api/v1/auth/me");

const A = "/api/admin";
export const api = {
  categories: () => request<Category[]>("GET", `${A}/categories`),
  createCategory: (name: string) => request<Category>("POST", `${A}/categories`, { name }),
  updateCategory: (id: number, name: string) => request<Category>("PUT", `${A}/categories/${id}`, { name }),
  deleteCategory: (id: number) => request<void>("DELETE", `${A}/categories/${id}`),

  books: (page: number, q: string) =>
    request<BookPage>("GET", `${A}/books?page=${page}&page_size=20${q ? `&q=${encodeURIComponent(q)}` : ""}`),
  book: (id: number) => request<Book>("GET", `${A}/books/${id}`),
  createBook: (b: BookInput) => request<Book>("POST", `${A}/books`, b),
  updateBook: (id: number, b: BookInput) => request<Book>("PUT", `${A}/books/${id}`, b),
  deleteBook: (id: number) => request<void>("DELETE", `${A}/books/${id}`),

  uploadCover: (id: number, file: File) => {
    const f = new FormData();
    f.append("file", file);
    return request<Book>("POST", `${A}/books/${id}/cover`, undefined, f);
  },
  uploadDigital: (id: number, file: File) => {
    const f = new FormData();
    f.append("file", file);
    return request<Book>("POST", `${A}/books/${id}/digital-file`, undefined, f);
  },
  removeDigital: (id: number) => request<Book>("DELETE", `${A}/books/${id}/digital-file`),

  orderSummary: () => request<{ awaiting_confirmation: number; to_ship: number }>("GET", `${A}/orders/summary`),
  orders: (page: number, status: OrderStatus | "", q: string) => {
    const p = new URLSearchParams({ page: String(page), page_size: "20" });
    if (status) p.set("status", status);
    if (q) p.set("q", q);
    return request<OrderPage>("GET", `${A}/orders?${p}`);
  },
  order: (id: number) => request<Order>("GET", `${A}/orders/${id}`),
  confirmPayment: (id: number) => request<Order>("POST", `${A}/orders/${id}/confirm-payment`),
  rejectPayment: (id: number, reason: string) => request<Order>("POST", `${A}/orders/${id}/reject-payment`, { reason }),
  shipOrder: (id: number, tracking_code: string) => request<Order>("POST", `${A}/orders/${id}/ship`, { tracking_code: tracking_code || null }),
  completeOrder: (id: number) => request<Order>("POST", `${A}/orders/${id}/complete`),
  cancelOrder: (id: number, reason: string) => request<Order>("POST", `${A}/orders/${id}/cancel`, { reason }),
  patchOrder: (id: number, patch: Partial<Pick<Order, "postal_code" | "admin_note" | "tracking_code">>) =>
    request<Order>("PATCH", `${A}/orders/${id}`, patch),
};
