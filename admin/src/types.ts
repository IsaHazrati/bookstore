export type BookType = "physical" | "digital" | "both";

export interface Category {
  id: number;
  name: string;
  slug: string;
}

export interface Book {
  id: number;
  title: string;
  slug: string;
  author: string;
  publisher: string | null;
  isbn: string | null;
  description: string;
  cover_image_url: string | null;
  published_date: string | null;
  book_type: BookType;
  price: string;
  stock_quantity: number;
  is_published: boolean;
  category_id: number | null;
  category: Category | null;
  has_digital_file: boolean;
}

export interface BookPage {
  items: Book[];
  total: number;
  page: number;
  page_size: number;
}

export interface BookInput {
  title: string;
  slug: string | null;
  author: string;
  publisher: string | null;
  isbn: string | null;
  description: string;
  published_date: string | null;
  book_type: BookType;
  price: number;
  stock_quantity: number;
  is_published: boolean;
  category_id: number | null;
}

export interface Me {
  id: number;
  email: string;
  full_name: string;
  role: "customer" | "admin";
}

export type OrderStatus = "pending_payment" | "awaiting_confirmation" | "paid" | "shipped" | "completed" | "cancelled";

export interface OrderItem {
  book_id: number;
  book_slug: string | null;
  item_type: "physical" | "digital";
  quantity: number;
  title: string;
  unit_price: string;
}

export interface Order {
  id: number;
  status: OrderStatus;
  subtotal: string;
  shipping_fee: string;
  total_price: string;
  recipient_name: string | null;
  phone: string | null;
  province: string | null;
  city: string | null;
  shipping_address: string | null;
  postal_code: string | null;
  customer_note: string | null;
  payment_reference: string | null;
  tracking_code: string | null;
  cancel_reason: string | null;
  admin_note: string | null;
  user_email: string | null;
  expires_at: string | null;
  payment_submitted_at: string | null;
  paid_at: string | null;
  shipped_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  items: OrderItem[];
}

export interface OrderPage {
  items: Order[];
  total: number;
  page: number;
  page_size: number;
}
