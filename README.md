# کتاب‌فروشی آنلاین

FastAPI + Next.js (فروشگاه) + React/Vite (ادمین) + PostgreSQL + Nginx، همه با Docker.

## اجرا

```bash
cp .env.example .env      # سپس مقادیر را عوض کنید
docker compose up --build
```

- فروشگاه: http://bookstore.localhost
- پنل مدیریت: http://admin.bookstore.localhost
- تست سلامت: http://bookstore.localhost/api/v1/health

## آپلودها

کاورها و فایل‌های دیجیتال در volume به نام `uploads` (مسیر `/data/uploads`) می‌مانند و با `docker compose down` پاک نمی‌شوند. فقط `covers/` عمومی است (`/media/covers/...`)؛ پوشه‌ی `digital/` هرگز سرو نمی‌شود. از این volume پشتیبان بگیر.

## سفارش و پرداخت (مرحله ۵)

- قیمت‌ها در دیتابیس و API به **ریال** و در فروشگاه/پنل به **تومان** هستند. در پنل ادمین قیمت را به تومان وارد کنید.
- پرداخت فعلاً **کارت‌به‌کارت** است: `PAYMENT_CARD_NUMBER` و `PAYMENT_CARD_HOLDER` را در `.env` بگذارید. مشتری شماره پیگیری را ثبت می‌کند و ادمین در تب «سفارش‌ها» تأیید یا رد می‌کند.
- هزینه‌ی ارسال ثابت: `SHIPPING_FEE_RIAL` (ریال). سفارش پرداخت‌نشده بعد از ۴۸ ساعت خودکار لغو و موجودی آزاد می‌شود.
- کد پستی هنگام خرید پرسیده نمی‌شود؛ هنگام ارسال از مشتری بگیرید و در جزئیات سفارش وارد کنید.
- کتاب دیجیتال بعد از تأیید پرداخت در «حساب من» با لینک ۵ دقیقه‌ای (حداکثر ۱۰ دانلود) قابل دریافت است؛ فایل را nginx مستقیم از volume سرو می‌کند.
- **ورود مشتری به HTTPS نیاز دارد** (کوکی Secure). قبل از راه‌اندازی HTTPS فقط برای تست `COOKIE_SECURE=false` بگذارید.

## کش فروشگاه

کش ISR و داده‌ی Next.js در حافظه با سقف تعداد نگه داشته می‌شود (`storefront/cache-handler.js`)، نه روی دیسک. سقف پیش‌فرض ۱۰۰۰ ورودی است و با متغیر `NEXT_CACHE_MAX_ENTRIES` قابل تغییر است. با ری‌استارت کانتینر کش خالی می‌شود و صفحات در اولین بازدید دوباره ساخته می‌شوند.

## ساخت ادمین اولیه

ثبت‌نام عمومی فقط «مشتری» می‌سازد. ادمین را از روی سرور بساز:

```bash
docker compose exec backend python -m app.scripts.create_admin you@example.com
```

## تست بک‌اند

```bash
cd backend && pip install -r requirements-dev.txt && pytest
```

## ساختار

- `backend/` — API (مسیرهای `/api/v1` برای فروشگاه و `/api/admin` برای مدیریت)
- `storefront/` — فروشگاه با SSR/ISR برای سئو
- `admin/` — پنل مدیریت (دامنه‌ی جدا، noindex)
- `nginx/` — مسیریابی دو دامنه؛ `/api/admin` روی دامنه‌ی عمومی مسدود است
