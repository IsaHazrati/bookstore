"use client";
import Link from "next/link";
import { cartCount, useCart } from "@/lib/cart";

export default function HeaderNav() {
  const count = cartCount(useCart());
  return (
    <nav className="user-nav" aria-label="حساب و سبد">
      <Link href="/account">حساب من</Link>
      <Link href="/cart" className="cart-link">
        سبد خرید{count > 0 && <span className="count" aria-label={`${count} مورد`}>{count.toLocaleString("fa-IR")}</span>}
      </Link>
    </nav>
  );
}
