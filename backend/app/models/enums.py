import enum


class Role(str, enum.Enum):
    customer = "customer"
    admin = "admin"


class BookType(str, enum.Enum):
    physical = "physical"
    digital = "digital"
    both = "both"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class ItemType(str, enum.Enum):
    physical = "physical"
    digital = "digital"
