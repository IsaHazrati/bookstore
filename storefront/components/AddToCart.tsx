"use client";
import Link from "next/link";
import { useState } from "react";
import { addToCart, type ItemType } from "@/lib/cart";

interface Props {
  book: {
    id: number; title: string; slug: string; price: string; cover_image_url: string | null;
    book_type: "physical" | "digital" | "both"; in_stock: boolean; has_digital: boolean;
  };
}

export default function AddToCart({ book }: Props) {
  const [added, setAdded] = useState<ItemType | null>(null);
  const canPhysical = book.book_type !== "digital";
  const canDigital = book.book_type !== "physical" && book.has_digital;

  const add = (item_type: ItemType) => {
    addToCart({ book_id: book.id, item_type, title: book.title, slug: book.slug, price: book.price, cover: book.cover_image_url });
    setAdded(item_type);
  };

  if (!canPhysical && !canDigital) return null;
  return (
    <div className="buy">
      {canPhysical && (
        <button onClick={() => add("physical")} disabled={!book.in_stock}>
          {book.in_stock ? "افزودن نسخه‌ی چاپی به سبد" : "نسخه‌ی چاپی ناموجود"}
        </button>
      )}
      {canDigital && (
        <button className={canPhysical ? "secondary" : undefined} onClick={() => add("digital")}>
          افزودن نسخه‌ی دیجیتال به سبد
        </button>
      )}
      {added && (
        <p className="notice" role="status">
          {added === "digital" ? "نسخه‌ی دیجیتال" : "نسخه‌ی چاپی"} به سبد اضافه شد. <Link href="/cart">مشاهده‌ی سبد ←</Link>
        </p>
      )}
    </div>
  );
}
