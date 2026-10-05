"""قوانین سفارش: ثبت با کسر اتمی موجودی، چرخه‌ی وضعیت، انقضا و دسترسی دیجیتال.

همه‌ی تغییر وضعیت‌ها از اینجا می‌گذرند تا API مشتری و پنل ادمین یک قانون واحد داشته باشند.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import delete, exists, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.catalog import Book
from app.models.digital_access import DigitalAccess
from app.models.enums import BookType, ItemType, OrderStatus
from app.models.order import Order, OrderItem
from app.models.user import User
from app.schemas.orders import OrderCreate

S = OrderStatus

# انتقال‌های مجاز. هر چیز دیگری 409 است.
ALLOWED: dict[OrderStatus, set[OrderStatus]] = {
    S.pending_payment: {S.awaiting_confirmation, S.paid, S.cancelled},
    # «رد پرداخت» توسط ادمین سفارش را به انتظار پرداخت برمی‌گرداند
    S.awaiting_confirmation: {S.paid, S.pending_payment, S.cancelled},
    S.paid: {S.shipped, S.completed, S.cancelled},
    S.shipped: {S.completed},
    S.completed: set(),
    S.cancelled: set(),
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    # SQLite تاریخ را بدون timezone برمی‌گرداند؛ همه‌جا UTC فرض می‌شود
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def _err(code: int, detail: str) -> HTTPException:
    return HTTPException(code, detail)


def load_order(db: Session, order_id: int, *, user_id: int | None = None, lock: bool = False) -> Order:
    stmt = select(Order).options(selectinload(Order.items).selectinload(OrderItem.book)).where(Order.id == order_id)
    if user_id is not None:
        stmt = stmt.where(Order.user_id == user_id)  # سفارش دیگران = 404، نه 403
    if lock:
        stmt = stmt.with_for_update(of=Order)
    order = db.scalar(stmt)
    if order is None:
        raise _err(404, "order not found")
    return order


def _restore_stock(db: Session, order: Order) -> None:
    for item in order.items:
        if item.item_type == ItemType.physical:
            db.execute(
                update(Book).where(Book.id == item.book_id)
                .values(stock_quantity=Book.stock_quantity + item.quantity)
                .execution_options(synchronize_session=False)
            )


def transition(db: Session, order: Order, to: OrderStatus, *, reason: str | None = None) -> None:
    """تغییر وضعیت با همه‌ی اثرهای جانبی. commit با فراخواننده است."""
    if to not in ALLOWED[order.status]:
        raise _err(409, f"cannot change order from {order.status.value} to {to.value}")
    if to == S.shipped and not order.has_physical:
        raise _err(409, "order has no physical items to ship")
    now = utcnow()
    if to == S.cancelled:
        _restore_stock(db, order)
        # دسترسی‌های دیجیتالی که همین سفارش داده بود پس گرفته می‌شود
        db.execute(delete(DigitalAccess).where(DigitalAccess.order_id == order.id))
        order.cancelled_at, order.cancel_reason = now, reason
    elif to == S.paid:
        order.paid_at = now
        _grant_digital_access(db, order)
    elif to == S.shipped:
        order.shipped_at = now
    elif to == S.completed:
        order.completed_at = now
    elif to == S.awaiting_confirmation:
        order.payment_submitted_at = now
    order.status = to
    # سفارش صرفاً دیجیتال چیزی برای ارسال ندارد: بعد از تأیید پرداخت، تمام است
    if to == S.paid and not order.has_physical:
        order.status, order.completed_at = S.completed, now


def _grant_digital_access(db: Session, order: Order) -> None:
    max_downloads = get_settings().max_downloads_per_book
    for item in order.items:
        if item.item_type != ItemType.digital:
            continue
        owned = db.scalar(select(exists().where(DigitalAccess.user_id == order.user_id, DigitalAccess.book_id == item.book_id)))
        if not owned:
            db.add(DigitalAccess(user_id=order.user_id, book_id=item.book_id, order_id=order.id, max_downloads=max_downloads))
    db.flush()


def expire_stale_orders(db: Session) -> int:
    """سفارش‌های pending_payment که مهلتشان گذشته را لغو می‌کند و موجودی را آزاد می‌کند."""
    stale = db.scalars(
        select(Order).options(selectinload(Order.items))
        .where(Order.status == S.pending_payment, Order.expires_at < utcnow())
        .with_for_update(of=Order, skip_locked=True)
    ).all()
    for order in stale:
        transition(db, order, S.cancelled, reason="payment deadline passed")
    if stale:
        db.commit()
    return len(stale)


def create_order(db: Session, user: User, data: OrderCreate) -> Order:
    settings = get_settings()
    expire_stale_orders(db)

    seen: set[tuple[int, ItemType]] = set()
    for line in data.items:
        key = (line.book_id, line.item_type)
        if key in seen:
            raise _err(422, f"book {line.book_id} ({line.item_type.value}) appears twice; combine the quantities")
        seen.add(key)

    ids = {line.book_id for line in data.items}
    books = {b.id: b for b in db.scalars(select(Book).where(Book.id.in_(ids), Book.is_published.is_(True)))}

    lines: list[tuple[Book, ItemType, int]] = []
    for line in data.items:
        book = books.get(line.book_id)
        if book is None:
            raise _err(422, f"book {line.book_id} is not available")
        if line.item_type == ItemType.physical:
            if book.book_type not in (BookType.physical, BookType.both):
                raise _err(422, f"«{book.title}» has no printed edition")
            if line.quantity > settings.max_item_quantity:
                raise _err(422, f"at most {settings.max_item_quantity} copies of «{book.title}» per order")
        else:
            if book.book_type not in (BookType.digital, BookType.both) or not book.digital_file_path:
                raise _err(422, f"«{book.title}» has no digital edition")
            if line.quantity != 1:
                raise _err(422, "a digital book can only be bought once")
            owned = db.scalar(select(exists().where(DigitalAccess.user_id == user.id, DigitalAccess.book_id == book.id)))
            if owned:
                raise _err(409, f"you already own the digital edition of «{book.title}»")
        lines.append((book, line.item_type, line.quantity))

    has_physical = any(t == ItemType.physical for _, t, _ in lines)
    if has_physical and data.shipping is None:
        raise _err(422, "shipping details are required for printed books")

    # کسر اتمی موجودی: فقط اگر موجودی کافی باشد ردیف به‌روز می‌شود. ترتیب ثابت (بر اساس id)
    # از بن‌بست بین دو سفارش همزمان جلوگیری می‌کند. هر خطا کل تراکنش را برمی‌گرداند.
    try:
        for book, item_type, qty in sorted(lines, key=lambda x: x[0].id):
            if item_type != ItemType.physical:
                continue
            res = db.execute(
                update(Book).where(Book.id == book.id, Book.stock_quantity >= qty)
                .values(stock_quantity=Book.stock_quantity - qty)
                .execution_options(synchronize_session=False)
            )
            if res.rowcount != 1:
                raise _err(409, f"not enough stock for «{book.title}»")

        subtotal = sum((Decimal(b.price) * q for b, _, q in lines), Decimal(0))
        shipping_fee = Decimal(settings.shipping_fee_rial if has_physical else 0)
        order = Order(
            user_id=user.id,
            status=S.pending_payment,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            total_price=subtotal + shipping_fee,
            customer_note=(data.customer_note or "").strip() or None,
            expires_at=utcnow() + timedelta(hours=settings.order_payment_hours),
            items=[OrderItem(book_id=b.id, item_type=t, quantity=q, title=b.title, unit_price=b.price) for b, t, q in lines],
        )
        if has_physical and data.shipping:
            sh = data.shipping
            order.recipient_name, order.phone = sh.recipient_name, sh.phone
            order.province, order.city, order.shipping_address = sh.province, sh.city, sh.address
        db.add(order)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return load_order(db, order.id)


def submit_payment(db: Session, order: Order, reference: str) -> None:
    if order.status == S.pending_payment and order.expires_at and _aware(order.expires_at) < utcnow():
        raise _err(409, "the payment deadline for this order has passed")
    if order.status == S.awaiting_confirmation:
        # اصلاح شماره پیگیری قبل از بررسی ادمین
        order.payment_reference, order.payment_submitted_at = reference, utcnow()
        return
    order.payment_reference = reference
    transition(db, order, S.awaiting_confirmation)
