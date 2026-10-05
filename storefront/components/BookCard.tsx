import Link from "next/link";
import type { Book } from "@/lib/api";
import { TYPE_LABEL, toman } from "@/lib/format";

export default function BookCard({ book }: { book: Book }) {
  return (
    <article className="card book">
      <Link href={`/books/${book.slug}`} className="cover-link" aria-label={book.title}>
        {book.cover_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={book.cover_image_url} alt={`جلد کتاب ${book.title}`} width={160} height={230} loading="lazy" />
        ) : (
          <div className="cover-empty" aria-hidden>کتاب</div>
        )}
      </Link>
      <h3><Link href={`/books/${book.slug}`}>{book.title}</Link></h3>
      <p className="muted">{book.author}</p>
      <p className="row-between">
        <strong>{toman(book.price)}</strong>
        <span className="badge">{TYPE_LABEL[book.book_type]}</span>
      </p>
      {book.book_type === "physical" && !book.in_stock && <p className="out">ناموجود</p>}
    </article>
  );
}
