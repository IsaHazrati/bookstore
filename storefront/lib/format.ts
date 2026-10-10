import type { BookType } from "./api";

/** مبالغ در API به ریال‌اند؛ به کاربر همیشه تومان نشان داده می‌شود. */
export const toman = (rial: string | number) => `${Math.round(Number(rial) / 10).toLocaleString("fa-IR")} تومان`;

export const faDateTime = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString("fa-IR", { dateStyle: "medium", timeStyle: "short" }) : "";

export const TYPE_LABEL: Record<BookType, string> = {
  physical: "چاپی",
  digital: "دیجیتال",
  both: "چاپی و دیجیتال",
};

/** JSON را برای قرار دادن داخل <script> امن می‌کند (جلوگیری از بستن تگ با </script>). */
export const safeJsonLd = (data: unknown) => JSON.stringify(data).replace(/</g, "\\u003c");
