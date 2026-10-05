from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DigitalAccess(Base):
    """حق دانلود یک کتاب دیجیتال برای یک کاربر، پس از پرداخت سفارش."""

    __tablename__ = "digital_access"
    __table_args__ = (UniqueConstraint("user_id", "book_id", name="uq_digital_access_user_book"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    download_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    download_count: Mapped[int] = mapped_column(default=0)
    max_downloads: Mapped[int] = mapped_column(default=5)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
