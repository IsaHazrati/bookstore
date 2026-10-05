from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ItemType, OrderStatus

# همه‌ی مبالغ به ریال
Money = Numeric(14, 0)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        # رشته + CHECK (native_enum=False)؛ توضیح در OrderStatus
        Enum(OrderStatus, name="order_status", native_enum=False, length=30, create_constraint=True),
        default=OrderStatus.pending_payment,
        index=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(Money, default=0)
    shipping_fee: Mapped[Decimal] = mapped_column(Money, default=0)
    total_price: Mapped[Decimal] = mapped_column(Money, default=0)

    # گیرنده (فقط وقتی سفارش کالای فیزیکی دارد). کد پستی عمداً در فرم خرید پرسیده نمی‌شود؛
    # هنگام ارسال از مشتری گرفته و ادمین واردش می‌کند.
    recipient_name: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20))
    province: Mapped[str | None] = mapped_column(String(60))
    city: Mapped[str | None] = mapped_column(String(60))
    shipping_address: Mapped[str | None] = mapped_column(String(500))
    postal_code: Mapped[str | None] = mapped_column(String(10))
    customer_note: Mapped[str | None] = mapped_column(String(500))

    # پرداخت دستی: شماره پیگیری کارت‌به‌کارت که مشتری ثبت می‌کند
    payment_reference: Mapped[str | None] = mapped_column(String(120))
    # جای خالی درگاه پرداخت: بعداً شناسه تراکنش درگاه اینجا ذخیره می‌شود
    payment_gateway_ref: Mapped[str | None] = mapped_column(String(120))

    tracking_code: Mapped[str | None] = mapped_column(String(60))
    admin_note: Mapped[str | None] = mapped_column(String(1000))
    cancel_reason: Mapped[str | None] = mapped_column(String(300))

    # مهلت پرداخت؛ بعد از آن سفارش پرداخت‌نشده خودکار لغو و موجودی آزاد می‌شود
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="orders")  # noqa: F821
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )

    @property
    def has_physical(self) -> bool:
        return any(i.item_type == ItemType.physical for i in self.items)


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_items_price_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType, name="item_type"))
    quantity: Mapped[int] = mapped_column(default=1)
    # عنوان و قیمت لحظه‌ی خرید؛ با تغییر بعدی کتاب، فاکتور قدیمی عوض نمی‌شود
    title: Mapped[str] = mapped_column(String(255), default="", server_default="")
    unit_price: Mapped[Decimal] = mapped_column(Money)

    order: Mapped[Order] = relationship(back_populates="items")
