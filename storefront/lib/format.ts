import type { BookType } from "./api";

export const toman = (price: string | number) => `${Number(price).toLocaleString("fa-IR")} تومان`;

export const TYPE_LABEL: Record<BookType, string> = {
  physical: "چاپی",
  digital: "دیجیتال",
  both: "چاپی و دیجیتال",
};

/** JSON را برای قرار دادن داخل <script> امن می‌کند (جلوگیری از بستن تگ با </script>). */
export const safeJsonLd = (data: unknown) => JSON.stringify(data).replace(/</g, "\\u003c");
