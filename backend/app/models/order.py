from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ItemType, OrderStatus


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), default=OrderStatus.pending
    )
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 0), default=0)
    shipping_address: Mapped[str | None] = mapped_column(String(500))
    # جای خالی درگاه پرداخت: بعداً شناسه تراکنش درگاه اینجا ذخیره می‌شود
    payment_gateway_ref: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="orders")  # noqa: F821
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType, name="item_type"))
    quantity: Mapped[int] = mapped_column(default=1)
    # قیمت لحظه خرید؛ با تغییر قیمت کتاب بعداً عوض نمی‌شود
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 0))

    order: Mapped[Order] = relationship(back_populates="items")
