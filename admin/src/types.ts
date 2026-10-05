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
