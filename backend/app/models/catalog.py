from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(280), unique=True, index=True)
    author: Mapped[str] = mapped_column(String(160), index=True)
    publisher: Mapped[str | None] = mapped_column(String(160))
    isbn: Mapped[str | None] = mapped_column(String(20), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    published_date: Mapped[date | None] = mapped_column(Date)

    book_type: Mapped[BookType] = mapped_column(Enum(BookType, name="book_type"))
    # قیمت به تومان/ریال به‌صورت عدد صحیح‌مانند؛ Numeric برای جلوگیری از خطای اعشار
    price: Mapped[Decimal] = mapped_column(Numeric(12, 0))
    # فقط برای نسخه فیزیکی معنا دارد
    stock_quantity: Mapped[int] = mapped_column(default=0)
    # مسیر داخلی فایل روی دیسک سرور؛ هرگز به کلاینت برگردانده نمی‌شود
    digital_file_path: Mapped[str | None] = mapped_column(String(500))

    is_published: Mapped[bool] = mapped_column(default=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped[Category | None] = relationship(back_populates="books")
