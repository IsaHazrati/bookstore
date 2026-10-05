import Link from "next/link";

export default function NotFound() {
  return (
    <>
      <h1>صفحه پیدا نشد</h1>
      <p className="muted">این صفحه وجود ندارد یا دیگر در دسترس نیست.</p>
      <p><Link href="/books">مشاهده‌ی کتاب‌ها</Link></p>
    </>
  );
}
