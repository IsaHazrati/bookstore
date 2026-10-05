from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BookType


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class BookOut(BaseModel):
    """نمای عمومی کتاب. عمداً هیچ مسیر فایل دیجیتالی ندارد."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    author: str
    publisher: str | None
    isbn: str | None
    description: str
    cover_image_url: str | None
    published_date: date | None
    book_type: BookType
    price: Decimal
    in_stock: bool = False
    has_digital: bool = False
    category: CategoryOut | None


class BookPage(BaseModel):
    items: list[BookOut]
    total: int
    page: int
    page_size: int


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
