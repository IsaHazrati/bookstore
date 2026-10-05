from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.models.enums import Role

_hasher = PasswordHash.recommended()  # Argon2id
# برای یکسان نگه داشتن زمان پاسخ وقتی ایمیل وجود ندارد
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    return _hasher.verify(password, password_hash or _DUMMY_HASH) and password_hash is not None


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
