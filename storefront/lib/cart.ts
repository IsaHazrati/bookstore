"use client";
// سبد خرید در localStorage مرورگر. قیمت اینجا فقط برای نمایش است؛
// هنگام ثبت سفارش، بک‌اند قیمت و موجودی را از دیتابیس می‌خواند.
import { useSyncExternalStore } from "react";

export type ItemType = "physical" | "digital";

export interface CartItem {
  book_id: number;
  item_type: ItemType;
  quantity: number;
  title: string;
  slug: string;
  price: string; // ریال
  cover: string | null;
}

const KEY = "bookstore_cart_v1";
const EMPTY: CartItem[] = [];
let cache: CartItem[] | null = null;
const listeners = new Set<() => void>();

function read(): CartItem[] {
  if (cache) return cache;
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    cache = Array.isArray(parsed) ? parsed : [];
  } catch {
    cache = [];
  }
  return cache;
}

function write(items: CartItem[]) {
  cache = items;
  try {
    localStorage.setItem(KEY, JSON.stringify(items));
  } catch {
    /* حالت خصوصی یا فضای پر: سبد فقط تا بستن صفحه می‌ماند */
  }
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  const onStorage = (e: StorageEvent) => {
    if (e.key === KEY) {
      cache = null;
      listener();
    }
  };
  window.addEventListener("storage", onStorage); // هماهنگی بین تب‌ها
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

export function useCart(): CartItem[] {
  return useSyncExternalStore(subscribe, read, () => EMPTY);
}

const same = (a: CartItem, id: number, t: ItemType) => a.book_id === id && a.item_type === t;

export function addToCart(item: Omit<CartItem, "quantity">) {
  const items = read();
  const existing = items.find((i) => same(i, item.book_id, item.item_type));
  if (existing) {
    if (item.item_type === "digital") return; // نسخه‌ی دیجیتال یک بار خریده می‌شود
    write(items.map((i) => (i === existing ? { ...i, quantity: Math.min(i.quantity + 1, 10) } : i)));
  } else {
    write([...items, { ...item, quantity: 1 }]);
  }
}

export function setQuantity(bookId: number, type: ItemType, quantity: number) {
  const q = Math.max(1, Math.min(10, Math.floor(quantity) || 1));
  write(read().map((i) => (same(i, bookId, type) ? { ...i, quantity: type === "digital" ? 1 : q } : i)));
}

export function removeFromCart(bookId: number, type: ItemType) {
  write(read().filter((i) => !same(i, bookId, type)));
}

export function clearCart() {
  write([]);
}

export const cartSubtotal = (items: CartItem[]) => items.reduce((sum, i) => sum + Number(i.price) * i.quantity, 0);
export const cartCount = (items: CartItem[]) => items.reduce((n, i) => n + i.quantity, 0);
