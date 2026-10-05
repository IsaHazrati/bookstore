from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps.auth import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.enums import OrderStatus
from app.models.order import Order, OrderItem
from app.models.user import User
from app.schemas.orders import OrderCreate, OrderOut, OrderPage, PaymentInfoOut, PaymentSubmit
from app.services import orders as svc

router = APIRouter(tags=["orders"])


def order_out(order: Order) -> OrderOut:
    out = OrderOut.model_validate(order)
    for item_out, item in zip(out.items, order.items):
        item_out.book_slug = item.book.slug if item.book else None
    return out


@router.get("/payment-info", response_model=PaymentInfoOut)
def payment_info() -> PaymentInfoOut:
    s = get_settings()
    return PaymentInfoOut(card_number=s.payment_card_number, card_holder=s.payment_card_holder,
                          shipping_fee=s.shipping_fee_rial, payment_hours=s.order_payment_hours)


@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(data: OrderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OrderOut:
    return order_out(svc.create_order(db, user, data))


@router.get("/orders", response_model=OrderPage)
def my_orders(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=20, ge=1, le=100),
) -> OrderPage:
    svc.expire_stale_orders(db)
    base = select(Order).where(Order.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.options(selectinload(Order.items).selectinload(OrderItem.book))
        .order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return OrderPage(items=[order_out(o) for o in rows], total=total, page=page, page_size=page_size)


@router.get("/orders/{order_id}", response_model=OrderOut)
def my_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OrderOut:
    svc.expire_stale_orders(db)
    return order_out(svc.load_order(db, order_id, user_id=user.id))


@router.post("/orders/{order_id}/payment", response_model=OrderOut)
def submit_payment(
    order_id: int, data: PaymentSubmit, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> OrderOut:
    order = svc.load_order(db, order_id, user_id=user.id, lock=True)
    svc.submit_payment(db, order, data.reference)
    db.commit()
    return order_out(svc.load_order(db, order_id))


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OrderOut:
    order = svc.load_order(db, order_id, user_id=user.id, lock=True)
    # مشتری فقط سفارش پرداخت‌نشده را لغو می‌کند؛ بعد از ثبت پرداخت، لغو با ادمین است
    if order.status != OrderStatus.pending_payment:
        raise svc._err(409, "only unpaid orders can be cancelled; contact support")
    svc.transition(db, order, OrderStatus.cancelled, reason="cancelled by customer")
    db.commit()
    return order_out(svc.load_order(db, order_id))
