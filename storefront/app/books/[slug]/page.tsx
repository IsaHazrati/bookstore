import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import AddToCart from "@/components/AddToCart";
import { NotFoundError, absolute, getBook, type Book } from "@/lib/api";
import { TYPE_LABEL, safeJsonLd, toman } from "@/lib/format";

// صفحه‌ی کتاب: ISR. در اولین بازدید ساخته و هر ۶۰ ثانیه تازه می‌شود.
export const revalidate = 60;

// هیچ صفحه‌ای در build ساخته نمی‌شود (بک‌اند آن لحظه در دسترس نیست)؛
// هر کتاب در اولین بازدید ساخته و کش می‌شود (ISR روی‌درخواست).
export async function generateStaticParams() {
  return [];
}

type Props = { params: Promise<{ slug: string }> };

async function load(slug: string): Promise<Book> {
  try {
    return await getBook(decodeURIComponent(slug));
  } catch (e) {
    if (e instanceof NotFoundError) notFound();
    throw e;
  }
}

const summary = (b: Book) => {
  const text = (b.description || `${b.title} نوشته‌ی ${b.author}`).replace(/\s+/g, " ").trim();
  return text.length > 160 ? `${text.slice(0, 157)}…` : text;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  let book: Book;
  try {
    book = await getBook(decodeURIComponent(slug));
  } catch (e) {
    if (e instanceof NotFoundError) return { title: "کتاب پیدا نشد", robots: { index: false } };
    throw e;
  }
  const image = absolute(book.cover_image_url);
  return {
    title: `${book.title} — ${book.author}`,
    description: summary(book),
    alternates: { canonical: `/books/${book.slug}` },
    openGraph: {
      type: "book",
      title: book.title,
      description: summary(book),
      url: `/books/${book.slug}`,
      authors: [book.author],
      ...(book.isbn ? { isbn: book.isbn } : {}),
      ...(image ? { images: [{ url: image, alt: book.title }] } : {}),
    },
    twitter: { card: image ? "summary_large_image" : "summary" },
  };
}

function availability(b: Book): string {
  const ok = b.book_type === "digital" ? b.has_digital : b.book_type === "physical" ? b.in_stock : b.in_stock || b.has_digital;
  return `https://schema.org/${ok ? "InStock" : "OutOfStock"}`;
}

export default async function BookPage({ params }: Props) {
  const { slug } = await params;
  const book = await load(slug);

  // قیمت در API به ریال است؛ همان ارز ISO مورد نیاز schema.org (IRR)
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": ["Product", "Book"],
    name: book.title,
    author: { "@type": "Person", name: book.author },
    description: summary(book),
    ...(book.isbn ? { isbn: book.isbn } : {}),
    ...(book.publisher ? { publisher: { "@type": "Organization", name: book.publisher } } : {}),
    ...(book.published_date ? { datePublished: book.published_date } : {}),
    ...(book.cover_image_url ? { image: absolute(book.cover_image_url) } : {}),
    url: absolute(`/books/${book.slug}`),
    inLanguage: "fa",
    offers: {
      "@type": "Offer",
      price: String(Number(book.price)),
      priceCurrency: "IRR",
      availability: availability(book),
      url: absolute(`/books/${book.slug}`),
    },
  };

  const stock =
    book.book_type === "digital"
      ? { ok: book.has_digital, text: book.has_digital ? "نسخه‌ی دیجیتال در دسترس است" : "فعلاً در دسترس نیست" }
      : { ok: book.in_stock, text: book.in_stock ? "موجود در انبار" : "ناموجود" };

  return (
    <article>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: safeJsonLd(jsonLd) }} />
      <p className="crumbs">
        <Link href="/books">کتاب‌ها</Link>
        {book.category && <> / <Link href={`/categories/${book.category.slug}`}>{book.category.name}</Link></>}
      </p>
      <div className="detail">
        <div>
          {book.cover_image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={book.cover_image_url} alt={`جلد کتاب ${book.title}`} width={280} height={400} />
          ) : (
            <div className="cover-empty" style={{ aspectRatio: "7/10" }} aria-hidden>کتاب</div>
          )}
        </div>
        <div>
          <h1>{book.title}</h1>
          <p className="muted">نوشته‌ی {book.author}</p>
          <p className="price">{toman(book.price)}</p>
          <p>
            <span className="badge">{TYPE_LABEL[book.book_type]}</span>{" "}
            <span className={`stock${stock.ok ? "" : " no"}`}>{stock.text}</span>
          </p>
          <AddToCart book={book} />
          {book.book_type === "both" && book.has_digital && (
            <p className="muted">نسخه‌ی دیجیتال بلافاصله پس از پرداخت در حساب شما فعال می‌شود.</p>
          )}
          <dl className="meta">
            {book.publisher && (<><dt>ناشر</dt><dd>{book.publisher}</dd></>)}
            {book.isbn && (<><dt>شابک</dt><dd><bdi dir="ltr">{book.isbn}</bdi></dd></>)}
            {book.published_date && (<><dt>تاریخ انتشار</dt><dd>{new Date(book.published_date).toLocaleDateString("fa-IR")}</dd></>)}
          </dl>
          {book.description && (<><h2>درباره‌ی کتاب</h2><p className="desc">{book.description}</p></>)}
        </div>
      </div>
    </article>
  );
}
