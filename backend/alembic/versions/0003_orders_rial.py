"""orders for manual payment; prices in rial

- قیمت‌ها از تومان به ریال (×۱۰) و Numeric(14,0)
- وضعیت سفارش: enum خود PostgreSQL → VARCHAR + CHECK، با وضعیت‌های جدید
- فیلدهای گیرنده/پرداخت/زمان‌ها روی orders، snapshot عنوان روی order_items
- CHECK برای موجودی/قیمت/تعداد
- digital_access: حذف download_token (لینک‌ها حالا امضاشده و کوتاه‌عمرند)

Revision ID: 0003
Revises: 0002
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MONEY = sa.Numeric(14, 0)
OLD_MONEY = sa.Numeric(12, 0)
NEW_STATUSES = ("pending_payment", "awaiting_confirmation", "paid", "shipped", "completed", "cancelled")
TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    # ---- books: ریال + CHECK
    op.alter_column("books", "price", type_=MONEY, existing_type=OLD_MONEY, existing_nullable=False)
    op.execute("UPDATE books SET price = price * 10")
    op.create_check_constraint("ck_books_stock_nonnegative", "books", "stock_quantity >= 0")
    op.create_check_constraint("ck_books_price_nonnegative", "books", "price >= 0")

    # ---- orders: وضعیت رشته‌ای با نگاشت مقادیر قدیمی
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE VARCHAR(30) USING status::text")
    op.execute("UPDATE orders SET status = 'pending_payment' WHERE status = 'pending'")
    op.execute("UPDATE orders SET status = 'completed' WHERE status = 'delivered'")
    op.execute("DROP TYPE IF EXISTS order_status")
    op.create_check_constraint("order_status", "orders", f"status IN {NEW_STATUSES}")
    op.create_index("ix_orders_status", "orders", ["status"])

    op.alter_column("orders", "total_price", type_=MONEY, existing_type=OLD_MONEY, existing_nullable=False)
    op.execute("UPDATE orders SET total_price = total_price * 10")
    op.add_column("orders", sa.Column("subtotal", MONEY, nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("shipping_fee", MONEY, nullable=False, server_default="0"))
    op.execute("UPDATE orders SET subtotal = total_price")
    for name, type_ in [
        ("recipient_name", sa.String(120)), ("phone", sa.String(20)), ("province", sa.String(60)),
        ("city", sa.String(60)), ("postal_code", sa.String(10)), ("customer_note", sa.String(500)),
        ("payment_reference", sa.String(120)), ("tracking_code", sa.String(60)),
        ("admin_note", sa.String(1000)), ("cancel_reason", sa.String(300)),
        ("expires_at", TZ), ("payment_submitted_at", TZ), ("paid_at", TZ), ("shipped_at", TZ),
        ("completed_at", TZ), ("cancelled_at", TZ),
    ]:
        op.add_column("orders", sa.Column(name, type_, nullable=True))
    op.add_column("orders", sa.Column("updated_at", TZ, nullable=False, server_default=sa.text("now()")))

    # ---- order_items: ریال، snapshot عنوان، CHECK
    op.alter_column("order_items", "unit_price", type_=MONEY, existing_type=OLD_MONEY, existing_nullable=False)
    op.execute("UPDATE order_items SET unit_price = unit_price * 10")
    op.add_column("order_items", sa.Column("title", sa.String(255), nullable=False, server_default=""))
    op.execute("UPDATE order_items oi SET title = b.title FROM books b WHERE b.id = oi.book_id")
    op.create_check_constraint("ck_order_items_quantity_positive", "order_items", "quantity > 0")
    op.create_check_constraint("ck_order_items_price_nonnegative", "order_items", "unit_price >= 0")

    # ---- digital_access
    op.drop_index("ix_digital_access_download_token", table_name="digital_access")
    op.drop_column("digital_access", "download_token")
    op.alter_column("digital_access", "max_downloads", server_default="10", existing_type=sa.Integer())


def downgrade() -> None:
    op.alter_column("digital_access", "max_downloads", server_default=None, existing_type=sa.Integer())
    op.add_column("digital_access", sa.Column("download_token", sa.String(64), nullable=True))
    op.execute("UPDATE digital_access SET download_token = md5(random()::text || id::text)")
    op.alter_column("digital_access", "download_token", nullable=False)
    op.create_index("ix_digital_access_download_token", "digital_access", ["download_token"], unique=True)

    op.drop_constraint("ck_order_items_price_nonnegative", "order_items", type_="check")
    op.drop_constraint("ck_order_items_quantity_positive", "order_items", type_="check")
    op.drop_column("order_items", "title")
    op.execute("UPDATE order_items SET unit_price = unit_price / 10")
    op.alter_column("order_items", "unit_price", type_=OLD_MONEY, existing_type=MONEY, existing_nullable=False)

    for name in ("updated_at", "cancelled_at", "completed_at", "shipped_at", "paid_at", "payment_submitted_at",
                 "expires_at", "cancel_reason", "admin_note", "tracking_code", "payment_reference",
                 "customer_note", "postal_code", "city", "province", "phone", "recipient_name",
                 "shipping_fee", "subtotal"):
        op.drop_column("orders", name)
    op.execute("UPDATE orders SET total_price = total_price / 10")
    op.alter_column("orders", "total_price", type_=OLD_MONEY, existing_type=MONEY, existing_nullable=False)

    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_constraint("order_status", "orders", type_="check")
    op.execute("UPDATE orders SET status = 'pending' WHERE status IN ('pending_payment', 'awaiting_confirmation')")
    op.execute("UPDATE orders SET status = 'delivered' WHERE status = 'completed'")
    op.execute("CREATE TYPE order_status AS ENUM ('pending', 'paid', 'shipped', 'delivered', 'cancelled')")
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE order_status USING status::order_status")

    op.drop_constraint("ck_books_price_nonnegative", "books", type_="check")
    op.drop_constraint("ck_books_stock_nonnegative", "books", type_="check")
    op.execute("UPDATE books SET price = price / 10")
    op.alter_column("books", "price", type_=OLD_MONEY, existing_type=MONEY, existing_nullable=False)
