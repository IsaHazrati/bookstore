from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import exists, false, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.slug import slugify
from app.core.text import like_contains, search_key
from app.db.session import get_db
from app.models.catalog import Book, Category
from app.models.digital_access import DigitalAccess
from app.models.enums import BookType
from app.models.order import OrderItem
from app.schemas.admin_catalog import AdminBookOut, AdminBookPage, BookIn, CategoryIn
from app.schemas.catalog import CategoryOut
from app.services import storage

router = APIRouter(tags=["admin-catalog"])

COVER_URL_PREFIX = "/media/covers/"


# ---------- helpers ----------
def _unique_slug(db: Session, model, base: str, exclude_id: int | None = None) -> str:
    # slug + پسوند «-n» نباید از طول ستون بیشتر شود (قبلاً خطای ۵۰۰ می‌داد)
    max_len = model.__table__.c.slug.type.length
    base = base[:max_len].rstrip("-_") or "item"
    slug, n = base, 1
    while True:
        stmt = select(model.id).where(model.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(model.id != exclude_id)
        if db.scalar(stmt) is None:
            return slug
        n += 1
        suffix = f"-{n}"
        slug = base[: max_len - len(suffix)].rstrip("-_") + suffix


def _commit(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail)


def _get_book(db: Session, book_id: int) -> Book:
    book = db.scalar(select(Book).options(joinedload(Book.category)).where(Book.id == book_id))
    if book is None:
        raise HTTPException(404, "book not found")
    return book


def _book_out(book: Book) -> AdminBookOut:
    out = AdminBookOut.model_validate(book)
    out.has_digital_file = bool(book.digital_file_path)
    return out


def _check_rules(db: Session, data: BookIn, has_file: bool) -> None:
    if data.category_id is not None and db.get(Category, data.category_id) is None:
        raise HTTPException(422, "category does not exist")
    if data.book_type == BookType.physical and has_file:
        raise HTTPException(422, "physical-only book cannot have a digital file; remove the file first")
    if data.is_published and data.book_type in (BookType.digital, BookType.both) and not has_file:
        raise HTTPException(422, "upload the digital file before publishing a digital book")


def _apply(book: Book, data: BookIn) -> None:
    for field in ("title", "author", "publisher", "isbn", "description", "published_date",
                  "book_type", "price", "stock_quantity", "is_published", "category_id"):
        setattr(book, field, getattr(data, field))
    if data.book_type == BookType.digital:
        book.stock_quantity = 0  # موجودی برای کتاب صرفاً دیجیتال معنا ندارد


# ---------- categories ----------
@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)))


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(data: CategoryIn, db: Session = Depends(get_db)) -> Category:
    if db.scalar(select(Category.id).where(Category.name == data.name)):
        raise HTTPException(409, "category name already exists")
    cat = Category(name=data.name, slug=_unique_slug(db, Category, slugify(data.slug or data.name)))
    db.add(cat)
    _commit(db, "category already exists")
    return cat


@router.put("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, data: CategoryIn, db: Session = Depends(get_db)) -> Category:
    cat = db.get(Category, category_id)
    if cat is None:
        raise HTTPException(404, "category not found")
    if db.scalar(select(Category.id).where(Category.name == data.name, Category.id != category_id)):
        raise HTTPException(409, "category name already exists")
    cat.name = data.name
    if data.slug:
        cat.slug = _unique_slug(db, Category, slugify(data.slug), exclude_id=category_id)
    _commit(db, "category already exists")
    return cat


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> Response:
    cat = db.get(Category, category_id)
    if cat is None:
        raise HTTPException(404, "category not found")
    if db.scalar(select(func.count()).select_from(Book).where(Book.category_id == category_id)):
        raise HTTPException(409, "category still has books; move or delete them first")
    db.delete(cat)
    db.commit()
    return Response(status_code=204)


# ---------- books ----------
@router.get("/books", response_model=AdminBookPage)
def list_books(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AdminBookPage:
    stmt = select(Book)
    if q:
        key = search_key(q)
        stmt = stmt.where(Book.search_text.like(like_contains(key), escape="\\") if key else false())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.options(joinedload(Book.category)).order_by(Book.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).unique()
    return AdminBookPage(items=[_book_out(b) for b in rows], total=total, page=page, page_size=page_size)


@router.get("/books/{book_id}", response_model=AdminBookOut)
def get_book(book_id: int, db: Session = Depends(get_db)) -> AdminBookOut:
    return _book_out(_get_book(db, book_id))


@router.post("/books", response_model=AdminBookOut, status_code=201)
def create_book(data: BookIn, db: Session = Depends(get_db)) -> AdminBookOut:
    _check_rules(db, data, has_file=False)
    book = Book()
    _apply(book, data)
    book.slug = _unique_slug(db, Book, slugify(data.slug or data.title))
    db.add(book)
    _commit(db, "a book with this slug or ISBN already exists")
    return _book_out(_get_book(db, book.id))


@router.put("/books/{book_id}", response_model=AdminBookOut)
def update_book(book_id: int, data: BookIn, db: Session = Depends(get_db)) -> AdminBookOut:
    book = _get_book(db, book_id)
    _check_rules(db, data, has_file=bool(book.digital_file_path))
    _apply(book, data)
    if data.slug:
        book.slug = _unique_slug(db, Book, slugify(data.slug), exclude_id=book_id)
    _commit(db, "a book with this slug or ISBN already exists")
    return _book_out(_get_book(db, book_id))


@router.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db)) -> Response:
    book = _get_book(db, book_id)
    used = db.scalar(
        select(
            or_(
                exists().where(OrderItem.book_id == book_id),
                exists().where(DigitalAccess.book_id == book_id),
            )
        )
    )
    if used:
        raise HTTPException(409, "book appears in orders and cannot be deleted; unpublish it instead")
    cover = (book.cover_image_url or "").removeprefix(COVER_URL_PREFIX) or None
    digital = book.digital_file_path
    db.delete(book)
    db.commit()
    storage.delete_cover(cover)
    storage.delete_digital(digital)
    return Response(status_code=204)


# ---------- uploads ----------
# endpointها عمداً def معمولی‌اند (نه async): کار دیتابیس و دیسک همگام است و FastAPI
# آن‌ها را در threadpool اجرا می‌کند. نسخه‌ی async کل سرور را حین آپلود قفل می‌کرد.
@router.post("/books/{book_id}/cover", response_model=AdminBookOut)
def upload_cover(book_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)) -> AdminBookOut:
    book = _get_book(db, book_id)
    name = storage.save_cover(file)
    old = (book.cover_image_url or "").removeprefix(COVER_URL_PREFIX) or None
    book.cover_image_url = COVER_URL_PREFIX + name
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete_cover(name)
        raise
    storage.delete_cover(old)
    return _book_out(_get_book(db, book_id))


@router.post("/books/{book_id}/digital-file", response_model=AdminBookOut)
def upload_digital_file(
    book_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> AdminBookOut:
    book = _get_book(db, book_id)
    if book.book_type == BookType.physical:
        raise HTTPException(422, "physical-only book cannot have a digital file; change its type first")
    name = storage.save_digital(file)
    old = book.digital_file_path
    book.digital_file_path = name
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete_digital(name)
        raise
    storage.delete_digital(old)
    return _book_out(_get_book(db, book_id))


@router.delete("/books/{book_id}/digital-file", response_model=AdminBookOut)
def delete_digital_file(book_id: int, db: Session = Depends(get_db)) -> AdminBookOut:
    book = _get_book(db, book_id)
    if book.is_published and book.book_type in (BookType.digital, BookType.both):
        raise HTTPException(422, "unpublish the book or change its type before removing the digital file")
    old = book.digital_file_path
    book.digital_file_path = None
    db.commit()
    storage.delete_digital(old)
    return _book_out(_get_book(db, book_id))
