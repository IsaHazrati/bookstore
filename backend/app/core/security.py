import threading
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import get_settings
from app.models.enums import Role

# پارامترهای توصیه‌شده‌ی OWASP برای Argon2id (حدود ۱۹ مگابایت حافظه به‌ازای هر هش).
# پیش‌فرض قبلی ۶۴ مگابایت بود و ۴۰ ورود همزمان حافظه را به ~۱ گیگابایت می‌رساند.
# هش‌های قدیمی همچنان تأیید می‌شوند و در اولین ورود موفق با پارامترهای جدید بازنویسی می‌شوند.
_hasher = PasswordHash((Argon2Hasher(time_cost=2, memory_cost=19456, parallelism=1),))

# سقف تعداد هش همزمان: مصرف حافظه و CPU زیر سیل درخواست محدود می‌ماند.
_slots = threading.BoundedSemaphore(get_settings().password_hash_concurrency)
_SLOT_TIMEOUT_SECONDS = 10.0

# برای یکسان نگه داشتن زمان پاسخ وقتی ایمیل وجود ندارد
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


class PasswordHashingBusy(Exception):
    """همه‌ی اسلات‌های هش پر هستند؛ endpoint باید 503 برگرداند."""


def _acquire() -> None:
    if not _slots.acquire(timeout=_SLOT_TIMEOUT_SECONDS):
        raise PasswordHashingBusy


def hash_password(password: str) -> str:
    _acquire()
    try:
        return _hasher.hash(password)
    finally:
        _slots.release()


def verify_password(password: str, password_hash: str | None) -> tuple[bool, str | None]:
    """(درست است؟, هش جدید اگر پارامترها قدیمی بودند) را برمی‌گرداند."""
    _acquire()
    try:
        ok, new_hash = _hasher.verify_and_update(password, password_hash or _DUMMY_HASH)
    finally:
        _slots.release()
    if password_hash is None:
        return False, None
    return ok, new_hash


def create_access_token(user_id: int, role: Role) -> tuple[str, int]:
    """توکن و مدت اعتبارش (ثانیه) را برمی‌گرداند."""
    s = get_settings()
    minutes = s.admin_token_minutes if role == Role.admin else s.customer_token_minutes
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, s.secret_key, algorithm=s.jwt_algorithm), minutes * 60


def decode_access_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.secret_key, algorithms=[s.jwt_algorithm], options={"require": ["exp", "sub"]})
