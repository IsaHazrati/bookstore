from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import BookType
from app.schemas.catalog import CategoryOut


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=140)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v


class BookIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=280)
    author: str = Field(min_length=1, max_length=160)
    publisher: str | None = Field(default=None, max_length=160)
    isbn: str | None = Field(default=None, max_length=20)
    description: str = Field(default="", max_length=20000)
    published_date: date | None = None
    book_type: BookType
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=0)
    stock_quantity: int = Field(default=0, ge=0, le=1_000_000)
    is_published: bool = True
    category_id: int | None = None

    @field_validator("title", "author")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("isbn", "publisher")
    @classmethod
    def blank_to_none(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v else None


class AdminBookOut(BaseModel):
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
    stock_quantity: int
    is_published: bool
    category_id: int | None
    category: CategoryOut | None
    has_digital_file: bool = False


class AdminBookPage(BaseModel):
    items: list[AdminBookOut]
    total: int
    page: int
    page_size: int
