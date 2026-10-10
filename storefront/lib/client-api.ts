// فراخوانی API از مرورگر (صفحات سبد/حساب). nginx مسیر /api را روی همین دامنه به بک‌اند می‌دهد،
// پس کوکی HttpOnly نشست خودکار فرستاده می‌شود. هدر X-Requested-With محافظت CSRF بک‌اند است.

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

const MESSAGES: [RegExp, string | ((m: RegExpMatchArray) => string)][] = [
  [/incorrect email or password/, "ایمیل یا رمز عبور اشتباه است."],
  [/email already registered/, "این ایمیل قبلاً ثبت‌نام کرده است. وارد شوید."],
  [/not enough stock for «(.+)»/, (m) => `موجودی «${m[1]}» کافی نیست. تعداد را کم کنید یا آن را از سبد حذف کنید.`],
  [/already own the digital edition of «(.+)»/, (m) => `نسخه‌ی دیجیتال «${m[1]}» را قبلاً خریده‌اید؛ در کتابخانه‌ی شما هست.`],
  [/«(.+)» has no printed edition/, (m) => `«${m[1]}» نسخه‌ی چاپی ندارد.`],
  [/«(.+)» has no digital edition/, (m) => `«${m[1]}» نسخه‌ی دیجیتال ندارد.`],
  [/is not available/, "یکی از کتاب‌های سبد دیگر در دسترس نیست. سبد را بررسی کنید."],
  [/at most (\d+) copies of «(.+)»/, (m) => `از «${m[2]}» حداکثر ${Number(m[1]).toLocaleString("fa-IR")} نسخه در هر سفارش.`],
  [/shipping details are required/, "برای کتاب چاپی، اطلاعات گیرنده لازم است."],
  [/payment deadline/, "مهلت پرداخت این سفارش تمام شده است."],
  [/only unpaid orders can be cancelled/, "فقط سفارش پرداخت‌نشده قابل لغو است؛ با پشتیبانی تماس بگیرید."],
  [/download limit reached/, "سقف دانلود این کتاب پر شده است؛ با پشتیبانی تماس بگیرید."],
  [/access to this book has expired/, "مهلت دسترسی شما به این کتاب تمام شده است."],
  [/file is temporarily unavailable/, "فایل این کتاب موقتاً در دسترس نیست؛ با پشتیبانی تماس بگیرید."],
  [/server busy/, "سرور شلوغ است؛ چند لحظه بعد دوباره تلاش کنید."],
  [/cannot change order/, "وضعیت این سفارش تغییر کرده است؛ صفحه را تازه کنید."],
];

const FIELD_MESSAGES: Record<string, string> = {
  phone: "شماره موبایل معتبر وارد کنید (مثلاً ۰۹۱۲۱۲۳۴۵۶۷).",
  password: "رمز عبور باید حداقل ۸ کاراکتر باشد.",
  email: "ایمیل معتبر وارد کنید.",
  recipient_name: "نام گیرنده را کامل وارد کنید.",
  province: "استان را وارد کنید.",
  city: "شهر را وارد کنید.",
  address: "آدرس را کامل‌تر وارد کنید.",
  reference: "شماره پیگیری را کامل وارد کنید.",
};

function toPersian(status: number, detail: unknown): string {
  if (status === 429) return "تعداد تلاش‌ها زیاد بود. یک دقیقه صبر کنید و دوباره امتحان کنید.";
  if (typeof detail === "string") {
    for (const [re, msg] of MESSAGES) {
      const m = detail.match(re);
      if (m) return typeof msg === "function" ? msg(m) : msg;
    }
    return "خطایی رخ داد. دوباره تلاش کنید.";
  }
  if (Array.isArray(detail)) {
    for (const d of detail as { loc?: (string | number)[] }[]) {
      const field = (d.loc ?? []).filter((x) => typeof x === "string").pop() as string | undefined;
      if (field && FIELD_MESSAGES[field]) return FIELD_MESSAGES[field];
    }
    return "اطلاعات واردشده کامل یا معتبر نیست.";
  }
  return "خطایی رخ داد. دوباره تلاش کنید.";
}

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api/v1${path}`, {
      method: init.method ?? "GET",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Requested-With": "fetch" },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
    });
  } catch {
    throw new ApiError(0, "ارتباط با سرور برقرار نشد. اتصال اینترنت را بررسی کنید.");
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, toPersian(res.status, (data as { detail?: unknown }).detail));
  return data as T;
}

// ---- انواع داده‌ی API
export type OrderStatus = "pending_payment" | "awaiting_confirmation" | "paid" | "shipped" | "completed" | "cancelled";

export interface Me { id: number; email: string; full_name: string; role: string }

export interface OrderItem {
  book_id: number; book_slug: string | null; item_type: "physical" | "digital"; quantity: number; title: string; unit_price: string;
}

export interface Order {
  id: number; status: OrderStatus; subtotal: string; shipping_fee: string; total_price: string;
  recipient_name: string | null; phone: string | null; province: string | null; city: string | null;
  shipping_address: string | null; postal_code: string | null; customer_note: string | null;
  payment_reference: string | null; tracking_code: string | null; cancel_reason: string | null;
  expires_at: string | null; payment_submitted_at: string | null; paid_at: string | null; shipped_at: string | null;
  completed_at: string | null; cancelled_at: string | null; created_at: string; items: OrderItem[];
}

export interface LibraryItem {
  access_id: number; book_id: number; title: string; author: string; slug: string; cover_image_url: string | null;
  file_format: string | null; download_count: number; max_downloads: number; downloads_left: number;
}

export interface PaymentInfo { card_number: string; card_holder: string; shipping_fee: number; payment_hours: number }

export const STATUS_LABEL: Record<OrderStatus, string> = {
  pending_payment: "در انتظار پرداخت",
  awaiting_confirmation: "در انتظار تأیید پرداخت",
  paid: "پرداخت‌شده، آماده‌ی ارسال",
  shipped: "ارسال‌شده",
  completed: "تکمیل‌شده",
  cancelled: "لغوشده",
};
