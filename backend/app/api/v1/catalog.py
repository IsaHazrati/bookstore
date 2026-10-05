from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.catalog import Book, Category
from app.models.enums import BookType
from app.schemas.catalog import BookOut, BookPage, CategoryOut

router = APIRouter(tags=["catalog"])


def book_to_out(book: Book) -> BookOut:
    out = BookOut.model_validate(book)
    out.in_stock = book.book_type in (BookType.physical, BookType.both) and book.stock_quantity > 0
    out.has_digital = book.book_type in (BookType.digital, BookType.both) and bool(book.digital_file_path)
    return out


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)))


@router.get("/books", response_model=BookPage)
def list_books(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=100, description="جستجو در عنوان/نویسنده"),
    category: str | None = Query(default=None, description="slug دسته‌بندی"),
    book_type: BookType | None = None,
    sort: Literal["newest", "price_asc", "price_desc", "title"] = "newest",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> BookPage:
    stmt = select(Book).where(Book.is_published.is_(True))
    if q:
        like = f"%{_escape_like(q.strip().lower())}%"
        stmt = stmt.where(
            or_(func.lower(Book.title).like(like, escape="\\"), func.lower(Book.author).like(like, escape="\\"))
        )
    if category:
        stmt = stmt.join(Category).where(Category.slug == category)
    if book_type:
        # «both» هم در فیلتر فیزیکی و هم دیجیتال دیده می‌شود
        stmt = stmt.where(Book.book_type.in_([book_type, BookType.both]))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order = {
        "newest": (Book.created_at.desc(), Book.id.desc()),
        "price_asc": (Book.price.asc(), Book.id.asc()),
        "price_desc": (Book.price.desc(), Book.id.asc()),
        "title": (Book.title.asc(), Book.id.asc()),
    }[sort]
    rows = db.scalars(
        stmt.options(joinedload(Book.category)).order_by(*order).offset((page - 1) * page_size).limit(page_size)
    ).unique()
    return BookPage(items=[book_to_out(b) for b in rows], total=total, page=page, page_size=page_size)


@router.get("/books/{slug}", response_model=BookOut)
def get_book(slug: str, db: Session = Depends(get_db)) -> BookOut:
    book = db.scalar(
        select(Book).options(joinedload(Book.category)).where(Book.slug == slug, Book.is_published.is_(True))
    )
    if book is None:
        raise HTTPException(404, "book not found")
    return book_to_out(book)
