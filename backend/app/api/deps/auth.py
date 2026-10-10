import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import User

AUTH_COOKIE = "access_token"
CSRF_HEADER = "x-requested-with"
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

_bearer = HTTPBearer(auto_error=False)
_unauthorized = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="invalid or missing credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """کاربر از هدر Bearer (پنل ادمین) یا کوکی HttpOnly (فروشگاه) شناسایی می‌شود."""
    if creds is not None:
        token = creds.credentials
    else:
        token = request.cookies.get(AUTH_COOKIE)
        if token is None:
            raise _unauthorized
        # CSRF: مرورگر کوکی را خودکار می‌فرستد، ولی یک سایت دیگر نمی‌تواند هدر سفارشی
        # بفرستد مگر از CORS رد شود. پس درخواست تغییردهنده با کوکی باید این هدر را داشته باشد.
        if request.method not in _SAFE_METHODS and not request.headers.get(CSRF_HEADER):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "missing X-Requested-With header")
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise _unauthorized
    # نقش از دیتابیس خوانده می‌شود، نه از توکن: تغییر نقش/غیرفعال‌سازی فوراً اثر می‌کند
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    return user
