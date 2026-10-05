import type { Book } from "@/lib/api";
import BookCard from "./BookCard";

export default function BookGrid({ books }: { books: Book[] }) {
  if (books.length === 0) return <p className="muted">کتابی پیدا نشد.</p>;
  return (
    <div className="grid">
      {books.map((b) => <BookCard key={b.id} book={b} />)}
    </div>
  );
}
