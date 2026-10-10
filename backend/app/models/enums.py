import enum


class Role(str, enum.Enum):
    customer = "customer"
    admin = "admin"


class BookType(str, enum.Enum):
    physical = "physical"
    digital = "digital"
    both = "both"


class OrderStatus(str, enum.Enum):
    """چرخه‌ی سفارش با پرداخت دستی (کارت‌به‌کارت) تا وقتی درگاه اضافه شود.

    pending_payment ─(مشتری شماره پیگیری را ثبت می‌کند)→ awaiting_confirmation
        ─(ادمین تأیید می‌کند)→ paid ─(ارسال)→ shipped ─→ completed
    سفارش صرفاً دیجیتال بعد از تأیید مستقیم completed می‌شود.
    قبل از ارسال، لغو (cancelled) ممکن است و موجودی برمی‌گردد.
    در دیتابیس به‌صورت رشته + CHECK ذخیره می‌شود (نه enum خود PostgreSQL) تا اضافه کردن
    وضعیت جدید فقط یک تغییر ساده‌ی constraint باشد.
    """

    pending_payment = "pending_payment"
    awaiting_confirmation = "awaiting_confirmation"
    paid = "paid"
    shipped = "shipped"
    completed = "completed"
    cancelled = "cancelled"


class ItemType(str, enum.Enum):
    physical = "physical"
    digital = "digital"
