import type { Metadata } from "next";
import OrderView from "./OrderView";

export const metadata: Metadata = { title: "جزئیات سفارش", robots: { index: false, follow: false } };

export default function Page() {
  return <OrderView />;
}
