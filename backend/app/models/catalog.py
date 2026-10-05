from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Numeric, String, Text, event, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.text import search_key
from app.db.base import Base
from app.models.enums import BookType


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)

    books: Mapped[list["Book"]] = relationship(back_populates="category")


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("stock_quantity >= 0", name="ck_books_stock_nonnegative"),
        CheckConstraint("price >= 0", name="ck_books_price_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(280), unique=True, index=True)
    author: Mapped[str] = mapped_column(String(160), index=True)
    # کلید جستجوی یکسان‌شده‌ی عنوان + نویسنده؛ با event پایین خودکار پر می‌شود
    search_text: Mapped[str] = mapped_column(String(500), default="", server_default="")
    publisher: Mapped[str | None] = mapped_column(String(160))
    isbn: Mapped[str | None] = mapped_column(String(20), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    published_date: Mapped[date | None] = mapped_column(Date)

    book_type: Mapped[BookType] = mapped_column(Enum(BookType, name="book_type"))
    # قیمت به «ریال» (واحد درگاه‌های پرداخت ایرانی). نمایش به کاربر همیشه به تومان (÷۱۰) است.
    price: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    # فقط برای نسخه فیزیکی معنا دارد
    stock_quantity: Mapped[int] = mapped_column(default=0)
    # مسیر داخلی فایل روی دیسک سرور؛ هرگز به کلاینت برگردانده نمی‌شود
    digital_file_path: Mapped[str | None] = mapped_column(String(500))

    is_published: Mapped[bool] = mapped_column(default=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped[Category | None] = relationship(back_populates="books")


@event.listens_for(Book, "before_insert")
@event.listens_for(Book, "before_update")
def _sync_search_text(mapper, connection, target: Book) -> None:
    target.search_text = search_key(f"{target.title or ''} {target.author or ''}")
