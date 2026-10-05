from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """کلاس پایه‌ی همه‌ی مدل‌ها (در مرحله ۲ مدل‌ها از این ارث‌بری می‌کنند)."""
