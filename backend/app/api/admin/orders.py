import re
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.text import ascii_digits
from app.db.session import get_db
from app.models.enums import OrderStatus
from app.models.order import Order, OrderItem
from app.models.user import User
from app.schemas.orders import AdminOrderOut, AdminOrderPage
from app.services import orders as svc

router = APIRouter(tags=["admin-orders"])
S = OrderStatus


class ShipIn(BaseModel):
    tracking_code: str | None = Field(default=None, max_length=60)


class ReasonIn(BaseModel):
    reason: str = Field(min_length=2, max_length=300)


class OrderPatch(BaseModel):
    postal_code: str | None = Field(default=None, max_length=20)
    admin_note: str | None = Field(default=None, max_length=1000)
    tracking_code: str | None = Field(default=None, max_length=60)

    @field_validator("postal_code")
    @classmethod
    def postal(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        v = re.sub(r"[\s\-]", "", ascii_digits(v))
        if not re.fullmatch(r"\d{10}", v):
            raise ValueError("postal code must be 10 digits")
        return v


class Summary(BaseModel):
    awaiting_confirmation: int
    to_ship: int


def admin_out(order: Order) -> AdminOrderOut:
    out = AdminOrderOut.model_validate(order)
    out.user_email = order.user.email if order.user else None
    for item_out, item in zip(out.items, order.items):
        item_out.book_slug = item.book.slug if item.book else None
    return out


def _load(db: Session, order_id: int, lock: bool = False) -> Order:
    order = svc.load_order(db, order_id, lock=lock)
    db.refresh(order, ["user"])
    return order


@router.get("/orders/summary", response_model=Summary)
def summary(db: Session = Depends(get_db)) -> Summary:
    svc.expire_stale_orders(db)
    count = lambda st: db.scalar(select(func.count()).select_from(Order).where(Order.status == st)) or 0  # noqa: E731
    return Summary(awaiting_confirmation=count(S.awaiting_confirmation), to_ship=count(S.paid))


@router.get("/orders", response_model=AdminOrderPage)
def list_orders(
    db: Session = Depends(get_db),
    status: OrderStatus | None = None,
    q: str | None = Query(default=None, max_length=100, description="شماره سفارش، ایمیل، موبایل یا نام گیرنده"),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AdminOrderPage:
    svc.expire_stale_orders(db)
    stmt = select(Order).join(User, User.id == Order.user_id)
    if status:
        stmt = stmt.where(Order.status == status)
    if q and q.strip():
        term = ascii_digits(q.strip())
        like = "%" + term.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conds = [func.lower(User.email).like(like, escape="\\"), Order.phone.like(like, escape="\\"),
                 func.lower(Order.recipient_name).like(like, escape="\\")]
        if term.lstrip("#").isdigit():
            conds.append(Order.id == int(term.lstrip("#")))
        stmt = stmt.where(or_(*conds))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.options(selectinload(Order.items).selectinload(OrderItem.book), selectinload(Order.user))
        .order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return AdminOrderPage(items=[admin_out(o) for o in rows], total=total, page=page, page_size=page_size)


@router.get("/orders/{order_id}", response_model=AdminOrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)) -> AdminOrderOut:
    return admin_out(_load(db, order_id))


@router.post("/orders/{order_id}/confirm-payment", response_model=AdminOrderOut)
def confirm_payment(order_id: int, db: Session = Depends(get_db)) -> AdminOrderOut:
    order = svc.load_order(db, order_id, lock=True)
    svc.transition(db, order, S.paid)
    db.commit()
    return admin_out(_load(db, order_id))


@router.post("/orders/{order_id}/reject-payment", response_model=AdminOrderOut)
def reject_payment(order_id: int, data: ReasonIn, db: Session = Depends(get_db)) -> AdminOrderOut:
    """پرداخت پیدا نشد: سفارش به انتظار پرداخت برمی‌گردد و مهلت تازه می‌گیرد."""
    order = svc.load_order(db, order_id, lock=True)
    if order.status != S.awaiting_confirmation:
        raise HTTPException(409, "only orders awaiting confirmation can have their payment rejected")
    svc.transition(db, order, S.pending_payment)
    order.expires_at = svc.utcnow() + timedelta(hours=get_settings().order_payment_hours)
    note = f"payment rejected: {data.reason}"
    order.admin_note = f"{order.admin_note}\n{note}" if order.admin_note else note
    order.cancel_reason = None
    db.commit()
    return admin_out(_load(db, order_id))


@router.post("/orders/{order_id}/ship", response_model=AdminOrderOut)
def ship(order_id: int, data: ShipIn, db: Session = Depends(get_db)) -> AdminOrderOut:
    order = svc.load_order(db, order_id, lock=True)
    svc.transition(db, order, S.shipped)
    if data.tracking_code and data.tracking_code.strip():
        order.tracking_code = ascii_digits(data.tracking_code.strip())
    db.commit()
    return admin_out(_load(db, order_id))


@router.post("/orders/{order_id}/complete", response_model=AdminOrderOut)
def complete(order_id: int, db: Session = Depends(get_db)) -> AdminOrderOut:
    order = svc.load_order(db, order_id, lock=True)
    svc.transition(db, order, S.completed)
    db.commit()
    return admin_out(_load(db, order_id))


@router.post("/orders/{order_id}/cancel", response_model=AdminOrderOut)
def cancel(order_id: int, data: ReasonIn, db: Session = Depends(get_db)) -> AdminOrderOut:
    order = svc.load_order(db, order_id, lock=True)
    svc.transition(db, order, S.cancelled, reason=data.reason.strip())
    db.commit()
    return admin_out(_load(db, order_id))


@router.patch("/orders/{order_id}", response_model=AdminOrderOut)
def patch_order(order_id: int, data: OrderPatch, db: Session = Depends(get_db)) -> AdminOrderOut:
    order = svc.load_order(db, order_id, lock=True)
    for field in data.model_fields_set:  # فقط فیلدهایی که فرستاده شده‌اند
        value = getattr(data, field)
        if isinstance(value, str):
            value = value.strip() or None
        setattr(order, field, value)
    db.commit()
    return admin_out(_load(db, order_id))
