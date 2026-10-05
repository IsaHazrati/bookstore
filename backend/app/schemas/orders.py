import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.text import ascii_digits
from app.models.enums import ItemType, OrderStatus


def _clean(v: str) -> str:
    return re.sub(r"\s+", " ", v).strip()


class OrderLineIn(BaseModel):
    book_id: int
    item_type: ItemType
    quantity: int = Field(default=1, ge=1, le=100)


class ShippingIn(BaseModel):
    recipient_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(max_length=20)
    province: str = Field(min_length=2, max_length=60)
    city: str = Field(min_length=2, max_length=60)
    address: str = Field(min_length=5, max_length=500)

    @field_validator("recipient_name", "province", "city", "address")
    @classmethod
    def clean(cls, v: str) -> str:
        v = _clean(v)
        if len(v) < 2:
            raise ValueError("too short")
        return v

    @field_validator("phone")
    @classmethod
    def iran_mobile(cls, v: str) -> str:
        v = re.sub(r"[\s\-()]", "", ascii_digits(v))
        v = re.sub(r"^(\+98|0098|98)(?=9)", "0", v)
        if not re.fullmatch(r"09\d{9}", v):
            raise ValueError("enter a valid Iranian mobile number, e.g. 09121234567")
        return v


class OrderCreate(BaseModel):
    items: list[OrderLineIn] = Field(min_length=1, max_length=50)
    shipping: ShippingIn | None = None
    customer_note: str | None = Field(default=None, max_length=500)


class PaymentSubmit(BaseModel):
    reference: str = Field(min_length=4, max_length=120)

    @field_validator("reference")
    @classmethod
    def clean(cls, v: str) -> str:
        v = _clean(ascii_digits(v))
        if len(v) < 4:
            raise ValueError("too short")
        return v


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    book_id: int
    book_slug: str | None = None
    item_type: ItemType
    quantity: int
    title: str
    unit_price: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus
    subtotal: Decimal
    shipping_fee: Decimal
    total_price: Decimal
    recipient_name: str | None
    phone: str | None
    province: str | None
    city: str | None
    shipping_address: str | None
    postal_code: str | None
    customer_note: str | None
    payment_reference: str | None
    tracking_code: str | None
    cancel_reason: str | None
    expires_at: datetime | None
    payment_submitted_at: datetime | None
    paid_at: datetime | None
    shipped_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    items: list[OrderItemOut]


class AdminOrderOut(OrderOut):
    user_email: EmailStr | None = None
    admin_note: str | None


class OrderPage(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    page_size: int


class AdminOrderPage(BaseModel):
    items: list[AdminOrderOut]
    total: int
    page: int
    page_size: int


class PaymentInfoOut(BaseModel):
    card_number: str
    card_holder: str
    shipping_fee: int
    payment_hours: int
