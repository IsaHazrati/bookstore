"""ساخت (یا ارتقای) کاربر ادمین از روی سرور.

استفاده:
    python -m app.scripts.create_admin admin@example.com
(رمز به‌صورت تعاملی پرسیده می‌شود تا در history شل نماند؛ یا متغیر ADMIN_PASSWORD)
"""
import getpass
import os
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import Role
from app.models.user import User


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python -m app.scripts.create_admin <email>")
    email = sys.argv[1].lower()
    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Password: ")
    if len(password) < 8:
        sys.exit("password must be at least 8 characters")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.role = Role.admin
            user.password_hash = hash_password(password)
            action = "updated"
        else:
            db.add(User(email=email, password_hash=hash_password(password), role=Role.admin))
            action = "created"
        db.commit()
    print(f"admin {action}: {email}")


if __name__ == "__main__":
    main()
