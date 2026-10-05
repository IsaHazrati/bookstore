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
